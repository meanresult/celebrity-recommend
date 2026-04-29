from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.models import DagRun
from airflow.operators.empty import EmptyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.session import provide_session
from docker.types import Mount

from instagram_brand_factory import load_brand_configs


def build_brand_etl_deps() -> list[tuple[str, str, tuple[int, int]]]:
    deps: list[tuple[str, str, tuple[int, int]]] = []
    for config in load_brand_configs().values():
        if not config.enabled:
            continue
        deps.append((config.dag_id, "load_to_snowflake", config.utc_schedule))
    return deps


BRAND_ETL_DEPS = build_brand_etl_deps()
DBT_IMAGE = "insta_pipeline-dbt"
DOCKER_NETWORK = "insta_pipeline_default"


def build_transform_schedule() -> str:
    latest_hour = 0
    latest_minute = 0
    for config in load_brand_configs().values():
        if not config.enabled:
            continue
        hour, minute = config.utc_schedule
        if (hour, minute) > (latest_hour, latest_minute):
            latest_hour, latest_minute = hour, minute

    base = datetime(2026, 1, 1, latest_hour, latest_minute) + timedelta(minutes=30)
    return f"{base.minute} {base.hour} * * *"


TRANSFORM_SCHEDULE = build_transform_schedule()


default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}


def match_utc_time(hour: int, minute: int):
    def _fn(logical_date, **_):
        target = logical_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if logical_date < target:
            target -= timedelta(days=1)
        return target

    return _fn


@provide_session
def _latest_dagrun_state(dag_id: str, session=None) -> str | None:
    dag_run = (
        session.query(DagRun)
        .filter(DagRun.dag_id == dag_id)
        .order_by(DagRun.execution_date.desc())
        .first()
    )
    return dag_run.state if dag_run else None


SNOWFLAKE_ENV = {
    "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
    "SNOWFLAKE_USER": os.getenv("SNOWFLAKE_USER"),
    "SNOWFLAKE_PASSWORD": os.getenv("SNOWFLAKE_PASSWORD"),
    "SNOWFLAKE_ROLE": os.getenv("SNOWFLAKE_ROLE"),
    "SNOWFLAKE_WAREHOUSE": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "SNOWFLAKE_DATABASE": os.getenv("SNOWFLAKE_DATABASE"),
    "SNOWFLAKE_SCHEMA": os.getenv("SNOWFLAKE_SCHEMA"),
}


with DAG(
    dag_id="transform_dbt_after_all_brands",
    description="Wait for all configured Instagram ETL DAGs, then run dbt run/test via dbt Docker image",
    start_date=datetime(2026, 1, 1),
    schedule=TRANSFORM_SCHEDULE,
    catchup=False,
    default_args=default_args,
    tags=["transform", "dbt", "snowflake", "orchestration"],
) as dag:
    @task
    def start_marker():
        print("Transform DAG started. Waiting for all configured brand ETL DAGs to finish...")

    wait_sensors = []
    for etl_dag_id, etl_task_id, (hour, minute) in BRAND_ETL_DEPS:
        sensor = ExternalTaskSensor(
            task_id=f"wait__{etl_dag_id}__{etl_task_id}",
            external_dag_id=etl_dag_id,
            external_task_id=etl_task_id,
            allowed_states=["success"],
            failed_states=["failed", "skipped"],
            mode="reschedule",
            poke_interval=60,
            timeout=60 * 60 * 3,
            check_existence=True,
            execution_date_fn=match_utc_time(hour, minute),
        )
        wait_sensors.append(sensor)

    @task.branch(task_id="gate_for_manual")
    def gate_for_manual():
        from airflow.operators.python import get_current_context

        context = get_current_context()
        run_id = context["dag_run"].run_id
        is_manual = run_id.startswith("manual__")

        if not is_manual:
            return [sensor.task_id for sensor in wait_sensors]

        for etl_dag_id, _, _ in BRAND_ETL_DEPS:
            state = _latest_dagrun_state(etl_dag_id)
            if state != "success":
                return [sensor.task_id for sensor in wait_sensors]

        return "dbt_run"

    host_project_root = os.getenv("HOST_PROJECT_ROOT", "/Users/jeehun/Desktop/insta_pipeline")

    dbt_run = DockerOperator(
        task_id="dbt_run",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command="run",
        docker_url="unix://var/run/docker.sock",
        network_mode=DOCKER_NETWORK,
        mount_tmp_dir=False,
        mounts=[
            Mount(source=f"{host_project_root}/transform/insta_dbt", target="/usr/app", type="bind"),
            Mount(source=f"{host_project_root}/.dbt", target="/root/.dbt", type="bind"),
        ],
        working_dir="/usr/app",
        environment=SNOWFLAKE_ENV,
    )

    dbt_test = DockerOperator(
        task_id="dbt_test",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command="test",
        docker_url="unix://var/run/docker.sock",
        network_mode=DOCKER_NETWORK,
        mount_tmp_dir=False,
        mounts=[
            Mount(source=f"{host_project_root}/transform/insta_dbt", target="/usr/app", type="bind"),
            Mount(source=f"{host_project_root}/.dbt", target="/root/.dbt", type="bind"),
        ],
        working_dir="/usr/app",
        environment=SNOWFLAKE_ENV,
    )

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    gate = gate_for_manual()

    start >> start_marker() >> gate
    gate >> wait_sensors >> dbt_run
    gate >> dbt_run
    dbt_run >> dbt_test >> end

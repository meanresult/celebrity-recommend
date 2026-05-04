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
    """
    활성화된 브랜드 DAG의 (dag_id, 마지막 task_id, UTC 스케줄) 목록을 반환합니다.
    dbt DAG이 모든 브랜드 ETL의 완료를 기다릴 때 이 목록을 사용합니다.
    """
    deps: list[tuple[str, str, tuple[int, int]]] = []
    for config in load_brand_configs().values():
        if not config.enabled:
            continue
        deps.append((config.dag_id, "load_to_duckdb", config.utc_schedule))
    return deps


BRAND_ETL_DEPS = build_brand_etl_deps()
DBT_IMAGE = "insta_pipeline-dbt"
DOCKER_NETWORK = "insta_pipeline_default"


def build_transform_schedule() -> str:
    """
    모든 브랜드 ETL 중 가장 늦은 스케줄 + 30분 뒤를 dbt 실행 시각으로 결정합니다.
    (마지막 브랜드 수집이 끝난 직후 변환을 실행하기 위함)
    """
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
    """
    ExternalTaskSensor에 넘기는 execution_date_fn 생성기입니다.
    "오늘 HH:MM에 실행된 브랜드 DAG"을 가리키도록 날짜를 맞춰줍니다.
    아직 그 시각이 안 됐으면 전날 같은 시각으로 되돌립니다.
    """
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


DUCKDB_ENV = {
    "DUCKDB_PATH": os.getenv("DUCKDB_PATH", "/data/insta_pipeline.duckdb"),
}


with DAG(
    dag_id="transform_dbt_after_all_brands",
    description="Wait for all configured Instagram ETL DAGs, then run dbt run/test via dbt Docker image",
    start_date=datetime(2026, 1, 1),
    schedule=TRANSFORM_SCHEDULE,
    catchup=False,
    default_args=default_args,
    tags=["transform", "dbt", "duckdb", "orchestration"],
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
        """
        수동 실행(manual trigger)일 때는 모든 브랜드가 이미 성공 상태면
        센서 대기를 건너뛰고 바로 dbt_run으로 분기합니다.
        스케줄 실행이거나 아직 성공하지 않은 브랜드가 있으면 센서 대기로 이동합니다.
        """
        from airflow.operators.python import get_current_context

        context   = get_current_context()
        run_id    = context["dag_run"].run_id
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
        environment=DUCKDB_ENV,
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
        environment=DUCKDB_ENV,
    )

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    gate = gate_for_manual()

    start >> start_marker() >> gate
    gate >> wait_sensors >> dbt_run
    gate >> dbt_run
    dbt_run >> dbt_test >> end

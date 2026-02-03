from __future__ import annotations
import os 
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.providers.docker.operators.docker import DockerOperator

from airflow.models import DagRun
from airflow.utils.session import provide_session
from airflow.operators.empty import EmptyOperator
from docker.types import Mount




# ✅ 여기만 너 프로젝트에 맞게 수정하면 됨
BRAND_ETL_DEPS = [
    # (brand_etl_dag_id, 마지막 task_id, 실행 dag 실행시간(분)))
    ("insta_to_snowflake_dag_v4_amomento", "load_to_snowflake",(15,5)),
    ("insta_to_snowflake_dag_v4_cos", "load_to_snowflake",(15,10)),
    ("insta_to_snowflake_dag_v4_lemaire", "load_to_snowflake",(15,20)),
]

DBT_IMAGE = "insta_pipeline-dbt"
DOCKER_NETWORK = "insta_pipeline_default"


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
    """해당 DAG의 가장 최근 DagRun 상태(success/failed/running/...)"""
    dr = (
        session.query(DagRun)
        .filter(DagRun.dag_id == dag_id)
        .order_by(DagRun.execution_date.desc())
        .first()
    )
    return dr.state if dr else None

@task.branch(task_id="gate_for_manual")
def gate_for_manual():
    from airflow.operators.python import get_current_context

    ctx = get_current_context()
    run_id = ctx["dag_run"].run_id  # manual__..., scheduled__...
    is_manual = run_id.startswith("manual__")

    if not is_manual:
        # 스케줄 실행은 센서로 정상 대기
        return [s.task_id for s in wait_sensors]

    # 수동 실행이면: ETL DAG들이 이미 success인지 확인
    for etl_dag_id, _, _ in BRAND_ETL_DEPS:
        state = _latest_dagrun_state(etl_dag_id)
        if state != "success":
            # 하나라도 success 아니면 센서 태워서 기다리기
            return [s.task_id for s in wait_sensors]

    # 전부 success면 센서 스킵하고 바로 dbt_run
    return "dbt_run"

SNOWFLAKE_ENV = {
    'SNOWFLAKE_ACCOUNT': os.getenv('SNOWFLAKE_ACCOUNT'),
    'SNOWFLAKE_USER': os.getenv('SNOWFLAKE_USER'),
    'SNOWFLAKE_PASSWORD': os.getenv('SNOWFLAKE_PASSWORD'),
    'SNOWFLAKE_ROLE': os.getenv('SNOWFLAKE_ROLE'),
    'SNOWFLAKE_WAREHOUSE': os.getenv('SNOWFLAKE_WAREHOUSE'),
    'SNOWFLAKE_DATABASE': os.getenv('SNOWFLAKE_DATABASE'),
    'SNOWFLAKE_SCHEMA': os.getenv('SNOWFLAKE_SCHEMA'),
}


# ------------ DAG 정의 ------------------------------------------------------

with DAG(
    dag_id="transform_dbt_after_all_brands",
    description="Wait for all brand ETL DAGs, then run dbt run/test via dbt Docker image",
    start_date=datetime(2026, 1, 1),
    schedule="30 15 * * *",  # 예: ETL(00:05) 끝난 뒤 여유 두고 00:30에 변환 시작
    catchup=False,
    default_args=default_args,
    tags=["transform", "dbt", "snowflake", "orchestration"],
) as dag:



    @task
    def start_marker():
        # 실행 시작을 로그로 남기는 가벼운 태스크(선택)
        print("Transform DAG started. Waiting for all brand ETL DAGs to finish...")

    # ✅ 브랜드별 ETL 완료를 기다리는 센서들
    wait_sensors = []
    for etl_dag_id, etl_task_id , (h,m) in BRAND_ETL_DEPS:
        sensor = ExternalTaskSensor(
            task_id=f"wait__{etl_dag_id}__{etl_task_id}",
            external_dag_id=etl_dag_id,
            external_task_id=etl_task_id,
            allowed_states=["success"],
            failed_states=["failed", "skipped"],
            mode="reschedule",          # 워커 점유 최소화 (운영에서 보통 이걸 씀)
            poke_interval=60,           # 60초마다 확인
            timeout=60 * 60 * 3,        # 최대 3시간 기다리고 실패 처리
            check_existence=True,
            execution_date_fn=match_utc_time(h,m)  # 동일 실행시간 기준
        )
        wait_sensors.append(sensor)

    HOST_PROJECT_ROOT = os.getenv("HOST_PROJECT_ROOT", "/Users/jeehun/Desktop/INSTA_PIPELINE")  # 호스트 PC의 프로젝트 루트 경로

    # ✅ dbt run (docker compose: docker compose run --rm dbt run 과 같은 의미)
    dbt_run = DockerOperator(
        task_id="dbt_run",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,                   # --rm 역할
        command="run",
        docker_url="unix://var/run/docker.sock",
        network_mode=DOCKER_NETWORK,
        mount_tmp_dir=False,  # Docker-in-Docker 경고 해결
        mounts=[
            Mount(
                source=f"{HOST_PROJECT_ROOT}/transform/insta_dbt",
                target="/usr/app",
                type="bind"
            ),
            Mount(
                source=f"{HOST_PROJECT_ROOT}/.dbt",
                target="/root/.dbt",
                type="bind"
            ),
        ],
        working_dir="/usr/app",  # docker-compose의 working_dir와 동일
        environment=SNOWFLAKE_ENV,
)
    

    # ✅ dbt test
    dbt_test = DockerOperator(
        task_id="dbt_test",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command="test",
        docker_url="unix://var/run/docker.sock",
        network_mode=DOCKER_NETWORK,
                mount_tmp_dir=False,  # Docker-in-Docker 경고 해결
        mounts=[
            Mount(
                source=f"{HOST_PROJECT_ROOT}/transform/insta_dbt",
                target="/usr/app",
                type="bind"
            ),
            Mount(
                source=f"{HOST_PROJECT_ROOT}/.dbt",
                target="/root/.dbt",
                type="bind"
            ),
        ],
        working_dir="/usr/app",  # docker-compose의 working_dir와 동일
        environment=SNOWFLAKE_ENV,
    )

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    gate = gate_for_manual() # 브랜치 태스크

    start >> gate
    gate >> wait_sensors >> dbt_run
    gate >> dbt_run  # 수동 실행 시 센서 스킵
    dbt_run >> dbt_test >> end
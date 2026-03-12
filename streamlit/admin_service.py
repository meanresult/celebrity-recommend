from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd


KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class DagConfig:
    brand: str
    dag_id: str
    run_time_kst: time


DAG_CONFIGS = {
    "amomento": DagConfig(
        brand="amomento",
        dag_id="insta_to_snowflake_dag_v4_amomento",
        run_time_kst=time(0, 5),
    ),
    "cos": DagConfig(
        brand="cos",
        dag_id="insta_to_snowflake_dag_v4_cos",
        run_time_kst=time(0, 10),
    ),
    "lemaire": DagConfig(
        brand="lemaire",
        dag_id="insta_to_snowflake_dag_v4_lemaire",
        run_time_kst=time(0, 20),
    ),
}


def iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def build_logical_date(target_date_kst: date, config: DagConfig) -> str:
    kst_dt = datetime.combine(target_date_kst, config.run_time_kst, tzinfo=KST)
    return kst_dt.astimezone(timezone.utc).isoformat()


def build_execution_plan(selected_brands: list[str], start_date: date, end_date: date) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for brand in selected_brands:
        config = DAG_CONFIGS[brand]
        for target_date in iter_dates(start_date, end_date):
            rows.append(
                {
                    "브랜드": config.brand,
                    "DAG ID": config.dag_id,
                    "수집 기준일(KST)": target_date.isoformat(),
                    "실행 시각(KST)": config.run_time_kst.strftime("%H:%M"),
                    "logical_date(UTC)": build_logical_date(target_date, config),
                }
            )

    return pd.DataFrame(rows)


def resolve_airflow_container_name() -> str:
    command = [
        "docker",
        "ps",
        "--filter",
        "label=com.docker.compose.service=airflow",
        "--format",
        "{{.Names}}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "airflow 컨테이너 이름을 찾지 못했습니다.")

    container_name = result.stdout.strip().splitlines()
    if not container_name:
        raise RuntimeError("실행 중인 airflow 컨테이너를 찾지 못했습니다.")

    return container_name[0]


def trigger_dag_runs(selected_brands: list[str], start_date: date, end_date: date) -> pd.DataFrame:
    airflow_container = resolve_airflow_container_name()
    plan_df = build_execution_plan(selected_brands, start_date, end_date)
    results: list[dict[str, str]] = []

    for row in plan_df.to_dict(orient="records"):
        command = [
            "docker",
            "exec",
            "-i",
            airflow_container,
            "airflow",
            "dags",
            "trigger",
            "-e",
            row["logical_date(UTC)"],
            row["DAG ID"],
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        stdout_text = result.stdout.strip()
        stderr_text = result.stderr.strip()
        combined_text = "\n".join(part for part in [stdout_text, stderr_text] if part)

        if "DagRunAlreadyExists" in combined_text:
            status = "이미 존재함"
            message = "같은 날짜와 DAG run이 이미 생성되어 있어 새로 만들지 않았습니다."
        elif result.returncode == 0:
            status = "성공"
            message = stdout_text.splitlines()[-1] if stdout_text else "실행 완료"
        else:
            status = "실패"
            message = stderr_text or stdout_text or "실행 로그 없음"

        results.append(
            {
                **row,
                "실행 결과": status,
                "메시지": message,
            }
        )

    return pd.DataFrame(results)

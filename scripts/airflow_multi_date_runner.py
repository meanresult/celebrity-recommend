from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "KST 날짜 범위를 받아 Airflow DAG를 여러 날짜로 trigger 합니다. "
            "예: python3 scripts/airflow_multi_date_runner.py --brand amomento "
            "--start 2026-03-08 --end 2026-03-10"
        )
    )
    parser.add_argument(
        "--brand",
        required=True,
        choices=["amomento", "cos", "lemaire", "all"],
        help="실행할 브랜드. all을 주면 3개 브랜드를 모두 실행합니다.",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="수집 시작일(KST), 형식: YYYY-MM-DD",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="수집 종료일(KST), 형식: YYYY-MM-DD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 실행 없이 어떤 logical_date로 trigger 되는지만 출력합니다.",
    )
    return parser.parse_args()


def parse_kst_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"날짜 형식이 잘못되었습니다: {value}. YYYY-MM-DD 형식으로 입력하세요.") from exc


def iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def build_logical_date(target_date_kst: date, config: DagConfig) -> str:
    kst_dt = datetime.combine(target_date_kst, config.run_time_kst, tzinfo=KST)
    return kst_dt.astimezone(timezone.utc).isoformat()


def trigger_dag(config: DagConfig, logical_date: str, dry_run: bool) -> None:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "airflow",
        "airflow",
        "dags",
        "trigger",
        "-e",
        logical_date,
        config.dag_id,
    ]

    print(f"[{config.brand}] logical_date={logical_date} -> {config.dag_id}")

    if dry_run:
        print("  dry-run: 실행 생략")
        return

    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(f"실행 실패: {' '.join(command)}")


def main() -> None:
    args = parse_args()
    start_date = parse_kst_date(args.start)
    end_date = parse_kst_date(args.end)

    if start_date > end_date:
        raise SystemExit("start 날짜가 end 날짜보다 늦을 수 없습니다.")

    selected_configs = list(DAG_CONFIGS.values()) if args.brand == "all" else [DAG_CONFIGS[args.brand]]

    print("실행 대상:")
    for config in selected_configs:
        print(f"- {config.brand}: {config.dag_id} (KST {config.run_time_kst.strftime('%H:%M')})")

    print(f"KST 수집 범위: {start_date} ~ {end_date}")
    print("")

    for config in selected_configs:
        for target_date_kst in iter_dates(start_date, end_date):
            logical_date = build_logical_date(target_date_kst, config)
            trigger_dag(config, logical_date, args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("사용자가 실행을 중단했습니다.")

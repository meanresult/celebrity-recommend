from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.python import get_current_context

from utils import db as util


CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "brands.yaml"
POST_COLUMNS = [
    "post_id",
    "insta_id",
    "insta_name",
    "brand_name",
    "brand_id",
    "full_link",
    "img_src",
    "post_date",
    "tagged_insta_id",
    "tagged_insta_id_cnt",
]

def _parse_scalar(value: str):
    value = value.strip()
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def load_brand_records(config_path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped == "brands:":
            continue

        if stripped.startswith("- "):
            if current:
                records.append(current)
            current = {}
            stripped = stripped[2:]

        if current is None or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        current[key.strip()] = _parse_scalar(value)

    if current:
        records.append(current)

    return records



@dataclass(frozen=True)
class BrandDagConfig:
    brand_key: str
    instagram_id: str
    dag_id: str
    schedule: str
    enabled: bool
    schema: str = "RAW_DATA"
    table: str = "INSTAGRAM_POSTS"

    @property
    def utc_schedule(self) -> tuple[int, int]:
        minute_str, hour_str, *_ = self.schedule.split()
        return int(hour_str), int(minute_str)

    @property
    def kst_run_time(self) -> str:
        hour, minute = self.utc_schedule
        kst_hour = (hour + 9) % 24
        return f"{kst_hour:02d}:{minute:02d}"


def load_brand_configs(config_path: Path = CONFIG_PATH) -> dict[str, BrandDagConfig]:
    configs: dict[str, BrandDagConfig] = {}
    for item in load_brand_records(config_path):
        config = BrandDagConfig(
            brand_key=item["brand_key"],
            instagram_id=item["instagram_id"],
            dag_id=item["dag_id"],
            schedule=item["schedule"],
            enabled=bool(item.get("enabled", True)),
            schema=item.get("schema", "RAW_DATA"),
            table=item.get("table", "INSTAGRAM_POSTS"),
        )
        configs[config.brand_key] = config
    return configs


def create_instagram_brand_dag(config: BrandDagConfig) -> DAG | None:
    if not config.enabled:
        return None

    @task(task_id="print_run_date")
    def print_run_date() -> None:
        context = get_current_context()
        logical_date = context["logical_date"]
        data_interval_start = context["data_interval_start"]
        data_interval_end = context["data_interval_end"]
        logical_date_kst = logical_date.in_timezone("Asia/Seoul")

        print("LOGICAL_DATE raw:", logical_date, "tz:", logical_date.tzinfo)
        print("START raw:", data_interval_start, "tz:", data_interval_start.tzinfo)
        print("END   raw:", data_interval_end, "tz:", data_interval_end.tzinfo)
        print("LOGICAL_DATE KST:", logical_date_kst)
        print("START KST:", data_interval_start.in_timezone("Asia/Seoul"))
        print("END   KST:", data_interval_end.in_timezone("Asia/Seoul"))
        print("DATE_TO_PROCESS KST:", logical_date_kst.strftime("%Y-%m-%d"))

    @task(
        task_id="extract_instagram_data",
        pool="instagram_extract_pool",
        pool_slots=1,
        execution_timeout=timedelta(minutes=40),
    )
    def extract_instagram_data(debug: bool = True) -> str:
        from extractors.instagram_scraper import run

        context = get_current_context()
        logical_date_kst = context["logical_date"].in_timezone("Asia/Seoul")
        date_to_process = logical_date_kst.strftime("%Y-%m-%d")
        following_day = util.get_next_day(date_to_process)

        if debug:
            print(f"Processing data for date: {date_to_process} to {following_day}")

        posts = run(
            brand_id=config.instagram_id,
            brand_name=config.brand_key,
            headless=True,
            target_day=date_to_process,
        )

        dataframe = pd.DataFrame(posts, columns=POST_COLUMNS)
        tmp_dir = Variable.get("data_dir", default_var="/tmp/")
        file_path = util.get_file_path(tmp_dir, config.brand_key, context)

        dataframe.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(
            "\n"
            "[EXTRACT_TASK 요약]\n"
            f"logical_date={date_to_process}\n"
            f"brand={config.brand_key}\n"
            f"collected={len(posts)}\n"
            f"Data saved to {file_path}, total records: {len(dataframe)}"
        )
        return file_path

    @task(task_id="load_to_duckdb")
    def load_to_duckdb(filename: str) -> None:
        staging_table = f"temp_{config.table}"
        qualified_table = f"{config.schema}.{config.table}"
        conn = util.return_duckdb_conn()

        tmp_dir = Variable.get("data_dir", "/tmp/")
        file_path = util.get_file_path(tmp_dir, filename, get_current_context())

        try:
            util.ensure_instagram_posts_table(conn, config.schema, config.table)
            conn.execute(
                f"""
                CREATE TEMP TABLE {staging_table}(
                    post_id             VARCHAR,
                    insta_id            VARCHAR,
                    insta_name          VARCHAR,
                    brand_name          VARCHAR,
                    brand_id            VARCHAR,
                    full_link           VARCHAR,
                    img_src             VARCHAR,
                    post_date           VARCHAR,
                    tagged_insta_id     VARCHAR,
                    tagged_insta_id_cnt INTEGER
                );
                """
            )

            util.load_csv_to_table(conn, staging_table, file_path)

            row_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
            if row_count == 0:
                raise ValueError("스테이징에 적재된 데이터가 없습니다")

            duplicate_rows = conn.execute(
                f"""
                SELECT post_id, COUNT(*) AS cnt
                FROM {staging_table}
                GROUP BY post_id
                HAVING COUNT(*) > 1;
                """
            ).fetchall()
            if duplicate_rows:
                sample = ", ".join([f"{row[0]}({row[1]})" for row in duplicate_rows[:5]])
                raise ValueError(f"스테이징 post_id 중복 발견: {sample} ... (총 {len(duplicate_rows)}개)")

            invalid_post_id_count = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {staging_table}
                WHERE post_id IS NULL OR TRIM(post_id) = '';
                """
            ).fetchone()[0]
            if invalid_post_id_count > 0:
                raise ValueError(
                    f"스테이징에 비어있는 post_id가 {invalid_post_id_count}건 존재합니다."
                )

            upsert_sql = f"""
                MERGE INTO {qualified_table} AS target
                USING {staging_table} AS stage
                ON target.post_id = stage.post_id
                WHEN MATCHED THEN
                    UPDATE SET
                        insta_id            = stage.insta_id,
                        insta_name          = stage.insta_name,
                        last_seen_at        = CURRENT_TIMESTAMP,
                        active              = TRUE,
                        tagged_insta_id     = stage.tagged_insta_id,
                        tagged_insta_id_cnt = stage.tagged_insta_id_cnt
                WHEN NOT MATCHED THEN
                    INSERT (
                        post_id, insta_id, insta_name, brand_name, brand_id,
                        full_link, img_src, post_date,
                        first_seen_at, last_seen_at, active,
                        tagged_insta_id, tagged_insta_id_cnt
                    )
                    VALUES (
                        stage.post_id, stage.insta_id, stage.insta_name,
                        stage.brand_name, stage.brand_id,
                        stage.full_link, stage.img_src, stage.post_date,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE,
                        stage.tagged_insta_id, stage.tagged_insta_id_cnt
                    );
            """
            print("==== UPSERT SQL ====")
            print(upsert_sql)
            print("====================")
            conn.execute("BEGIN;")
            conn.execute(upsert_sql)
            conn.execute("COMMIT;")
            print(f"DuckDB 적재완료: {qualified_table}, {file_path}")
        except Exception as exc:
            conn.execute("ROLLBACK;")
            print(f"Error loading data: {exc}")
            raise exc
        finally:
            conn.close()

    with DAG(
        dag_id=config.dag_id,
        description=f"Instagram to DuckDB ETL DAG ({config.brand_key})",
        start_date=datetime(2026, 1, 8),
        catchup=False,
        tags=["ETL", "Instagram", "DuckDB", "incremental", "factory"],
        schedule=config.schedule,
    ) as dag:
        print_run_date() >> extract_instagram_data(debug=True) >> load_to_duckdb(config.brand_key)

    return dag

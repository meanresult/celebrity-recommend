import os
import time
from datetime import datetime, timedelta

import duckdb


# DuckDB 파일 위치. 환경변수로 덮어쓸 수 있습니다.
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/opt/airflow/data/insta_pipeline.duckdb")


# ──────────────────────────────────────────
# 1. 연결
# ──────────────────────────────────────────

def get_conn() -> duckdb.DuckDBPyConnection:
    # 여러 Airflow 태스크가 동시에 쓰기를 시도할 수 있어서,
    # 파일 잠금 해제를 최대 10번(30초) 기다린 뒤 포기합니다.
    for attempt in range(10):
        try:
            return duckdb.connect(DUCKDB_PATH)
        except duckdb.IOException:
            if attempt == 9:
                raise
            time.sleep(3)


# ──────────────────────────────────────────
# 2. 파일 경로
# ──────────────────────────────────────────

def get_file_path(tmp_dir: str, file_name: str, context) -> str:
    date = context["logical_date"].strftime("%Y%m%d")
    return os.path.join(tmp_dir, f"{file_name}_{date}.csv")


# ──────────────────────────────────────────
# 3. CSV 적재
# ──────────────────────────────────────────

def load_csv_to_table(conn: duckdb.DuckDBPyConnection, table: str, file_path: str) -> None:
    conn.execute(f"COPY {table} FROM '{file_path}' (FORMAT CSV, HEADER true)")


# ──────────────────────────────────────────
# 4. 테이블 초기화
# ──────────────────────────────────────────

def ensure_instagram_posts_table(conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> None:
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            post_id             VARCHAR PRIMARY KEY,
            insta_id            VARCHAR,
            insta_name          VARCHAR,
            brand_name          VARCHAR,
            brand_id            VARCHAR,
            full_link           VARCHAR,
            img_src             VARCHAR,
            post_date           DATE,
            first_seen_at       TIMESTAMPTZ,
            last_seen_at        TIMESTAMPTZ,
            active              BOOLEAN,
            tagged_insta_id     VARCHAR,
            tagged_insta_id_cnt INTEGER
        );
        """
    )


# ──────────────────────────────────────────
# 5. 날짜 유틸
# ──────────────────────────────────────────

def get_next_day(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")


def get_last_day(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")

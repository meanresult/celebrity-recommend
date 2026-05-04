import duckdb
import os
import time
from datetime import datetime, timedelta

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/opt/airflow/data/insta_pipeline.duckdb")

##################################
# 1. DuckDB 연결 함수
##################################

def return_duckdb_conn():
    for attempt in range(10):
        try:
            return duckdb.connect(DUCKDB_PATH)
        except duckdb.IOException:
            if attempt == 9:
                raise
            time.sleep(3)


##################################
# 2. 파일 경로 가져오는 함수
##################################

def get_file_path(tmp_dir, file_name, context):
    date = context['logical_date'].strftime('%Y%m%d')
    file_path = os.path.join(tmp_dir, f"{file_name}_{date}.csv")
    return file_path


##################################
# 3. CSV → DuckDB 테이블 적재 함수
##################################

def load_csv_to_table(conn, table, file_path):
    conn.execute(
        f"COPY {table} FROM '{file_path}' (FORMAT CSV, HEADER true)"
    )


##################################
# 4. 스키마/테이블 보장 함수
##################################

def ensure_instagram_posts_table(conn, schema, table):
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            post_id       VARCHAR PRIMARY KEY,
            insta_id      VARCHAR,
            insta_name    VARCHAR,
            brand_name    VARCHAR,
            brand_id      VARCHAR,
            full_link     VARCHAR,
            img_src       VARCHAR,
            post_date     DATE,
            first_seen_at TIMESTAMPTZ,
            last_seen_at  TIMESTAMPTZ,
            active        BOOLEAN,
            tagged_insta_id     VARCHAR,
            tagged_insta_id_cnt INTEGER
        );
        """
    )
    conn.execute(
        f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS insta_name VARCHAR;"
    )


##################################
# 5. 날짜 유틸
##################################

def get_next_day(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')


def get_last_day(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

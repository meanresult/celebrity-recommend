# 추후에 변경할 예정 
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from datetime import datetime, timedelta
import os 

##################################
# 💌 1. 스노우플레이크 연결(conn) 함수 
##################################

def return_snowflake_conn(snowflake_conn_id):
    hook = SnowflakeHook(snowflake_conn_id=snowflake_conn_id)

    conn = hook.get_conn()
    return conn.cursor()

##################################
# 💌 2. 파일 경로 가져오는 함수 
##################################

def get_file_path(tmp_dir, file_name, context):
    date = context['logical_date'].strftime('%Y%m%d')
    file_path = os.path.join(tmp_dir, f"{file_name}_{date}.csv")
    return file_path

##################################
# 💌 3. 스노우플레이크 테이블에 스테이지를 통해 데이터 적재 함수
##################################
def populate_table_via_stage(cur, table, file_path):

    table_stage = f"@%{table}"  # 테이블 스테이지 사용
    file_name = os.path.basename(file_path)

    # Internal table stage에 파일을 복사
    # 보통 이때 파일은 압축이 됨 (GZIP 등)
    cur.execute(f"PUT file://{file_path} {table_stage};")

    # Stage로부터 해당 테이블로 벌크 업데이트
    copy_query = f"""
        COPY INTO {table}(
            post_id,
            insta_id,
            brand_name,
            brand_id,
            full_link,
            img_src,
            post_date
        )
        FROM {table_stage}/{file_name}
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"' 
            SKIP_HEADER = 1
        )
    """
    cur.execute(copy_query)

##################################
# 💌 3.1 스노우플레이크 테이블에 스테이지를 통해 데이터 적재 함수
##################################
def populate_table_via_stage_v2(cur, table, file_path):

    table_stage = f"@%{table}"  # 테이블 스테이지 사용
    file_name = os.path.basename(file_path)

    # Internal table stage에 파일을 복사
    # 보통 이때 파일은 압축이 됨 (GZIP 등)
    cur.execute(f"PUT file://{file_path} {table_stage};")

    # Stage로부터 해당 테이블로 벌크 업데이트
    copy_query = f"""
        COPY INTO {table}(
            post_id,
            insta_id,
            brand_name,
            brand_id,
            full_link,
            img_src,
            post_date,
            tagged_insta_id,
            tagged_insta_id_cnt
        )
        FROM {table_stage}/{file_name}
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"' 
            SKIP_HEADER = 1
        )
    """
    cur.execute(copy_query)

##################################
# 💌 3.2 스키마/테이블 보장 함수
##################################
def ensure_instagram_posts_table(cur, schema, table):
    cur.execute("SELECT CURRENT_DATABASE()")
    current_database = cur.fetchone()[0]

    if not current_database:
        raise ValueError(
            "Snowflake connection에 기본 database가 설정되어 있지 않습니다. "
            "Airflow Connection(snowflake_conn)의 database 값을 확인하세요."
        )

    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    cur.execute(f"USE SCHEMA {schema};")
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            post_id STRING primary key,
            insta_id STRING,
            brand_name STRING,
            brand_id STRING,
            full_link STRING,
            img_src STRING,
            post_date DATE,
            first_seen_at TIMESTAMP_TZ,
            last_seen_at TIMESTAMP_TZ,
            active BOOLEAN,
            tagged_insta_id STRING,
            tagged_insta_id_cnt NUMBER
        );
        """
    )

##################################
# 💌 4. get_next_day: 다음 날짜 가져오는 함수
##################################
def get_next_day(date_str):
    """
    'YYYY-MM-DD' 형식의 날짜 문자열이 주어지면, 동일한 형식의 문자열로 다음 날짜를 반환
    """
    # 먼저 date_str을 datetime 객체로 변환
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    # 다음날 날짜를 계산
    return (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')


##################################
# 💌 5. get_last_day: 다음 날짜 가져오는 함수
##################################
def get_last_day(date_str):
    """
    'YYYY-MM-DD' 형식의 날짜 문자열이 주어지면, 동일한 형식의 문자열로 다음 날짜를 반환
    """
    # 먼저 date_str을 datetime 객체로 변환
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    # 다음날 날짜를 계산
    return (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

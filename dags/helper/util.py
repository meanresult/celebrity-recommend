# 추후에 변경할 예정 
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from datetime import datetime, timedelta
import os 

##################################
# 💌 1. 스노우플레이크 연결(conn) 함수 
##################################

def return_snowflake_conn(snowflake_conn_id):
    hook = SnowflakeHook(snowflake_conn_id="snowflake_conn")

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
        COPY INTO {table}
        FROM {table_stage}/{file_name}
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"' 
            SKIP_HEADER = 1
        )
    """
    cur.execute(copy_query)

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


def get_logical_date(context):
    return context['logical_date']

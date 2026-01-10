from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.operators.python import get_current_context


from helper import util
from extractors.main_mini_v7 import run
from datetime import datetime

import pandas as pd




@task
def extract_instagram_data(brand_id,brandname, debug: bool = True):
    context = get_current_context()

    # Airflow에게 어느 날짜의 데이터를 읽을지 문의
    date_to_process = str(context['logical_date'])[:10]
    following_day = util.get_next_day(date_to_process)
    
    if debug:
        print(f"Processing data for date: {date_to_process} to {following_day}")

    # 어제 날짜 데이처 추출
    # last_day = util.get_last_day(date_to_process)

    posts = run(
        brand_id=brand_id,
        brand_name=brandname,
        target=60,
        headless=True,  # Airflow에서는 브라우저 안 보이게
        target_day=date_to_process
    )
    df = pd.DataFrame(posts, columns=["post_id","insta_id","brand_name", "brand_id", "full_link", "img_src", "post_date"])
    
    tmp_dir = Variable.get("data_dir", default_var="/tmp/")
    file_path = util.get_file_path(tmp_dir,brandname,get_current_context())

    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"Data saved to {file_path}, total records: {len(df)}")
    return file_path

@task
def load_to_snowflake(filename, schema, table):
    cur = util.return_snowflake_conn("snowflake_fsh_conn")
    context = get_current_context()

    date_to_process = str(context['logical_date'])[:10] # 2024-01-08
    tmp_dir = Variable.get("data_dir", "/tmp/")
    file_path = util.get_file_path(tmp_dir, filename, get_current_context())

    """ Airflow의 읽어올 데이터의 날짜와 시간 관리를 위해 몇 개의 DAG RUN 변수 출력 """
    print("logical_date", context["logical_date"])
    print("data_interval_start", context["data_interval_start"])
    print("data_interval_end", context["data_interval_end"])

    try:
        df = pd.read_csv(file_path)
        if len(df) == 0:
            print(f"No data to load for date: {date_to_process}")
            return
        cur.execute(f"USE SCHEMA {schema};")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
            post_id STRING,
            insta_id STRING,
            brand_name STRING,
            brand_id STRING,
            full_link STRING,
            img_src STRING,
            post_date DATE
        );""")

        cur.execute("BEGIN;")
        cur.execute(f"DELETE FROM {table} WHERE post_date = '{date_to_process}';")

        for index, row in df.iterrows():
            sql = sql = f"""
                MERGE INTO {table} AS target
                USING (
                SELECT
                    %s AS post_id,
                    %s AS insta_id,
                    %s AS brand_name,
                    %s AS brand_id,
                    %s AS full_link,
                    %s AS img_src,
                    %s AS post_date
                ) AS source
                ON target.post_id = source.post_id
                WHEN MATCHED THEN UPDATE SET
                insta_id   = source.insta_id,
                brand_name = source.brand_name,
                brand_id   = source.brand_id,
                full_link  = source.full_link,
                img_src    = source.img_src,
                post_date  = source.post_date
                WHEN NOT MATCHED THEN INSERT (
                post_id, insta_id, brand_name, brand_id, full_link, img_src, post_date
                ) VALUES (
                source.post_id, source.insta_id, source.brand_name, source.brand_id,
                source.full_link, source.img_src, source.post_date
                );
                """
            cur.execute(sql, (row['post_id'],row['insta_id'],row['brand_name'],row['brand_id'], row['full_link'], row['img_src'], row['post_date']))
            cur.execute("COMMIT;")
    except Exception as e:
            cur.execute("ROLLBACK;")
            print(f"Error loading data: {e}")
            raise e
    finally:
        cur.close()

with DAG(
        dag_id="insta_to_snowflake_dag",
        description="Instagram to Snowflake ETL DAG",
        start_date=datetime(2026, 1, 8),
        catchup=False,
        tags=['ETL','Instagram','Snowflake','incremental'],
        schedule= '5 0 * * *',  # 매일 자정 5분 후 실행
) as dag:
    
    brand_id = "amomento.co"
    brandname = "amomento"
    schema = "RAW_DATA"
    table = "INSTAGRAM_POSTS"

    extract_instagram_data(brand_id, brandname, debug=True) >> load_to_snowflake(brandname, schema, table)

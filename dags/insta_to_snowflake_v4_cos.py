"""
목표 : 컬럼 추가 마지막 크롤링 날짜, 활성화 여부 
"""

from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.operators.python import get_current_context


from helper import util

from datetime import datetime

import pandas as pd

@task
def print_run_date():
    context = get_current_context()
    ld = context["logical_date"]
    dis = context["data_interval_start"]
    die = context["data_interval_end"]

    print("LOGICAL_DATE raw:", ld, "tz:", ld.tzinfo)
    print("START raw:", dis, "tz:", dis.tzinfo)
    print("END   raw:", die, "tz:", die.tzinfo)

    print("LOGICAL_DATE KST:", ld.in_timezone("Asia/Seoul"))
    print("START KST:", dis.in_timezone("Asia/Seoul"))
    print("END   KST:", die.in_timezone("Asia/Seoul"))

@task
def extract_instagram_data(brand_id,brandname, debug: bool = True):
    from extractors.main_mini_v10 import run
    context = get_current_context()

    # Airflow에게 어느 날짜의 데이터를 읽을지 문의
    logical_date_KST = context['logical_date']# .in_timezone("Asia/Seoul")

    date_to_process = str(logical_date_KST)[:10]
    following_day = util.get_next_day(date_to_process)
    
    if debug:
        print(f"Processing data for date: {date_to_process} to {following_day}")

    # 어제 날짜 데이처 추출
    # last_day = util.get_last_day(date_to_process)

    posts = run(
        brand_id=brand_id,
        brand_name=brandname,
        headless=True,  # Airflow에서는 브라우저 안 보이게
        target_day=date_to_process
    )

    # 인스타 브랜드 포스팅 게시물 테이블 저장

    df = pd.DataFrame(posts, columns=["post_id",
                                      "insta_id",
                                      "brand_name", 
                                      "brand_id", 
                                      "full_link", 
                                      "img_src", 
                                      "post_date",
                                      "tagged_insta_id",
                                      "tagged_insta_id_cnt"])
    
    tmp_dir = Variable.get("data_dir", default_var="/tmp/")
    file_path = util.get_file_path(tmp_dir,brandname,get_current_context())

    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"Data saved to {file_path}, total records: {len(df)}")

    return file_path

@task
def load_to_snowflake(filename, schema, table):

    staging_table = f"temp_{table}"

    cur = util.return_snowflake_conn("snowflake_fsh_conn")

    tmp_dir = Variable.get("data_dir", "/tmp/")
    file_path = util.get_file_path(tmp_dir, filename, get_current_context())

    # 실행 날짜 불러오기 
    date_to_process = str(get_current_context()['logical_date'])[:10] # 2024-01-08
    try:
        cur.execute(f"USE SCHEMA {schema};")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
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
        );""")


        cur.execute(f"""
            CREATE TEMPORARY TABLE {staging_table}(
                post_id STRING ,
                insta_id STRING,
                brand_name STRING,
                brand_id STRING,
                full_link STRING,
                img_src STRING,
                post_date STRING,
                tagged_insta_id STRING,
                tagged_insta_id_cnt NUMBER
            );
        """) #

        util.populate_table_via_stage_v2(cur,staging_table , file_path)
        
        cur.execute(f"SELECT COUNT(*) FROM {staging_table}")
        row_count = cur.fetchone()[0]

        if row_count == 0:
            raise ValueError("스테이징에 적재된 데이터가 없습니다")

        upsert_sql = f"""
            MERGE INTO {table} AS target
            USING {staging_table} AS stage
            on target.post_id = stage.post_id
            WHEN MATCHED THEN
                UPDATE SET
                last_seen_at = CURRENT_TIMESTAMP(),
                active       = TRUE,
                tagged_insta_id = stage.tagged_insta_id,
                tagged_insta_id_cnt = stage.tagged_insta_id_cnt

            WHEN NOT MATCHED THEN
                INSERT (post_id, insta_id, brand_name, brand_id, full_link,img_src,post_date,first_seen_at,last_seen_at,active,tagged_insta_id,tagged_insta_id_cnt)
                VALUES (stage.post_id, stage.insta_id, stage.brand_name, stage.brand_id, stage.full_link, stage.img_src, stage.post_date, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE,stage.tagged_insta_id,stage.tagged_insta_id_cnt);
        """

        print("==== UPSERT SQL ====")
        print(upsert_sql)
        print("====================")
        cur.execute(upsert_sql)
        print(f"스노우플레이크 적재완료: {staging_table},{file_path}")

    except Exception as e:
            cur.execute("ROLLBACK;")
            print(f"Error loading data: {e}")
            raise e
    finally:
        cur.close()


with DAG(
        dag_id="insta_to_snowflake_dag_v3_cos",
        description="Instagram to Snowflake ETL DAG",
        start_date=datetime(2026, 1, 8),
        catchup=False,
        tags=['ETL','Instagram','Snowflake','incremental'],
        schedule= '10 15 * * *',  # 매일 자정 5분 후 실행
) as dag:
    
    brand_id = "cosstores"
    brandname = "cos"
    schema = "RAW_DATA"
    table = (f"INSTAGRAM_POSTS")
    table_tag = (f"{brandname}_posted_tag")

    print_run_date() >>extract_instagram_data(brand_id, brandname, debug=True) >> load_to_snowflake(brandname, schema, table)

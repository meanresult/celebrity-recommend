from airflow import DAG
from aiflow.models import Variable
from extractors.main_mini_v5 import run
import pandas as pd


def return_snowflake_conn(warehouse: "COMPUTE_WH", database: "fsh"):
    user_id = Variable.get("SNOWFLAKE_USER_ID")
    password = Variable.get("SNOWFLAKE_PASSWORD")
    account = Variable.get("SNOWFLAKE_ACCOUNT")

    conn = snowflake.connector.connect(
        user=user_id,
        password=password,
        account=account,
        warehouse=warehouse,
        database=database)

    return conn.cursor()

def get_file_path(context):
    tmp_dir = Variable.get("data_dir", default_var="/tmp/")
    
    date = context['logical_date'].strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(tmp_dir, f"instagram_posts_{date}.csv")
    return file_path

@task
def extract_instagram_data():
    posts = run(
        tagged_url="https://www.instagram.com/amomento.co/tagged/",
        target=60,
        headless=True,  # Airflow에서는 브라우저 안 보이게
    )
    df = pd.DataFrame(posts, columns=["insta_id", "full_link", "img_src", "post_date"])
    file_path = get_file_path(get_current_context())

    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"Data saved to {file_path}, total records: {len(df)}")
    return file_path

@ task
def load_to_snowflake():
    # 파일 경로 가져오기
    file_path = get_file_path(get_current_context())
    # 파일명 추출
    file_name = os.path.basename(file_path)

    target_table = "INSTAGRAM_POSTS"
    target_stage = f"@%{target_table}"

    try:
        cur = return_snowflake_conn()
        cur.execute("USE SCHEMA FSH")

        cur.execute("BEGIN;")
        cur.execute(f"PUT file://{file_path} {target_stage} AUTO_COMPRESS
import os

import pandas as pd
import snowflake.connector
import streamlit as st


def get_snowflake_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def _execute_query(query: str) -> pd.DataFrame:
    conn = None
    cur = None
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetch_pandas_all()
    except Exception as exc:
        st.error(f"❌ 쿼리 실행 실패: {exc}")
        return pd.DataFrame()
    finally:
        try:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()
        except Exception:
            pass


@st.cache_data(ttl=600)
def run_query(query: str) -> pd.DataFrame:
    return _execute_query(query)

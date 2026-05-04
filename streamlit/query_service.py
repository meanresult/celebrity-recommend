import os

import duckdb
import pandas as pd
import streamlit as st

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/opt/airflow/data/insta_pipeline.duckdb")


def _execute_query(query: str) -> pd.DataFrame:
    conn = None
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        return conn.execute(query).df()
    except Exception as exc:
        st.error(f"❌ 쿼리 실행 실패: {exc}")
        return pd.DataFrame()
    finally:
        if conn is not None:
            conn.close()


@st.cache_data(ttl=600)
def run_query(query: str) -> pd.DataFrame:
    return _execute_query(query)

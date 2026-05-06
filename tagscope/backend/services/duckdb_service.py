from __future__ import annotations

import os

import duckdb
import pandas as pd

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/opt/airflow/data/insta_pipeline.duckdb")


def run_query(sql: str, params: list | None = None) -> pd.DataFrame:
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        result = conn.execute(sql, params or []).fetchdf()
        result.columns = [c.upper() for c in result.columns]
        return result
    finally:
        conn.close()

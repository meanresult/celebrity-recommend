from fastapi import APIRouter

from services.duckdb_service import run_query

router = APIRouter(prefix="/api/freshness", tags=["freshness"])

_SQL = """
SELECT
    MAX(last_seen_at) AS last_loaded_at,
    MAX(post_date) AS latest_post_date
FROM RAW_DATA.INSTAGRAM_POSTS
"""


@router.get("")
def get_freshness() -> dict:
    df = run_query(_SQL)
    if df.empty:
        return {"last_loaded_at": None, "latest_post_date": None}
    row = df.iloc[0]
    return {
        "last_loaded_at": str(row["LAST_LOADED_AT"]) if row["LAST_LOADED_AT"] else None,
        "latest_post_date": str(row["LATEST_POST_DATE"]) if row["LATEST_POST_DATE"] else None,
    }

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from queries.co_brand_queries import (
    build_co_brand_detail_query,
    build_co_brand_kpi_query,
    build_co_brand_ranking_query,
)
from services.duckdb_service import run_query

router = APIRouter(prefix="/api/co-brands", tags=["co-brands"])


class CoBrandRequest(BaseModel):
    brands: list[str]


@router.post("")
def get_co_brands(req: CoBrandRequest) -> dict:
    if not req.brands:
        raise HTTPException(status_code=400, detail="brands must not be empty")

    kpi_df = run_query(build_co_brand_kpi_query(req.brands))
    ranking_df = run_query(build_co_brand_ranking_query(req.brands))

    kpi = {}
    if not kpi_df.empty:
        row = kpi_df.iloc[0]
        kpi = {
            "total_accounts": int(row["TOTAL_ACCOUNTS"] or 0),
            "co_brand_count": int(row["CO_BRAND_COUNT"] or 0),
        }

    rows = []
    for _, r in ranking_df.iterrows():
        rows.append({
            "rank": int(r["RANK"]),
            "tagged_account": str(r["TAGGED_ACCOUNT"]),
            "tagger_count": int(r["TAGGER_COUNT"]),
            "total_tag_count": int(r["TOTAL_TAG_COUNT"]),
            "tagger_ratio": float(r["TAGGER_RATIO"]),
        })

    return {"kpi": kpi, "rows": rows}


@router.get("/{tagged_account}")
def get_co_brand_detail(tagged_account: str, brands: str = "") -> dict:
    brand_list = [b.strip() for b in brands.split(",") if b.strip()]
    if not brand_list:
        raise HTTPException(status_code=400, detail="brands query param required")

    df = run_query(build_co_brand_detail_query(tagged_account, brand_list))

    result: dict = {"taggers": [], "monthly": []}
    for _, row in df.iterrows():
        section = str(row["SECTION"])
        raw = row["DATA"]
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        result[section] = parsed

    return result

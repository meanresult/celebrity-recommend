from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from queries.tagger_queries import (
    build_tagger_count_query,
    build_tagger_detail_query,
    build_tagger_kpi_query,
    build_tagger_list_query,
)
from services.duckdb_service import run_query

router = APIRouter(prefix="/api/taggers", tags=["taggers"])


class TaggerRequest(BaseModel):
    brands: list[str]
    page: int = 1
    page_size: int = 20


@router.post("")
def get_taggers(req: TaggerRequest) -> dict:
    if not req.brands:
        raise HTTPException(status_code=400, detail="brands must not be empty")

    kpi_df = run_query(build_tagger_kpi_query(req.brands))
    count_df = run_query(build_tagger_count_query(req.brands))
    total = int(count_df.iloc[0]["TOTAL"]) if not count_df.empty else 0
    offset = (req.page - 1) * req.page_size

    list_df = run_query(build_tagger_list_query(req.brands, req.page_size, offset))

    kpi = {}
    if not kpi_df.empty:
        row = kpi_df.iloc[0]
        kpi = {
            "total_accounts": int(row["TOTAL_ACCOUNTS"] or 0),
            "avg_tag_count": float(row["AVG_TAG_COUNT"] or 0),
            "top_tagger_id": str(row["TOP_TAGGER_ID"]) if row["TOP_TAGGER_ID"] else None,
            "top_tagger_name": str(row["TOP_TAGGER_NAME"]) if row["TOP_TAGGER_NAME"] else None,
            "top_tagger_count": int(row["TOP_TAGGER_COUNT"]) if pd.notna(row["TOP_TAGGER_COUNT"]) else 0,
        }

    rows = []
    for _, r in list_df.iterrows():
        rows.append({
            "rank": int(r["RANK"]),
            "insta_id": str(r["INSTA_ID"]),
            "insta_name": str(r["INSTA_NAME"]),
            "tag_count": int(r["TAG_COUNT"]),
            "latest_tag_date": str(r["LATEST_TAG_DATE"]) if r["LATEST_TAG_DATE"] else None,
            "other_brand_count": int(r["OTHER_BRAND_COUNT"]),
        })

    return {
        "kpi": kpi,
        "rows": rows,
        "total": total,
        "page": req.page,
        "page_size": req.page_size,
    }


@router.get("/{insta_id}")
def get_tagger_detail(insta_id: str, brands: str = "") -> dict:
    brand_list = [b.strip() for b in brands.split(",") if b.strip()]
    if not brand_list:
        raise HTTPException(status_code=400, detail="brands query param required")

    df = run_query(build_tagger_detail_query(insta_id, brand_list))

    result: dict = {"profile": {}, "top_brands": [], "recent_posts": []}
    for _, row in df.iterrows():
        section = str(row["SECTION"])
        raw = row["DATA"]
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        result[section] = parsed

    return result

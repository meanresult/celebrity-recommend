from __future__ import annotations

import pandas as pd


DEFAULT_SELECTED_BRANDS = ["amomento.co", "lemaire"]


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def extract_brand_options(brand_df: pd.DataFrame) -> list[str]:
    if brand_df.empty or "TAGGED_ACCOUNT" not in brand_df.columns:
        return []
    return brand_df["TAGGED_ACCOUNT"].dropna().tolist()


def build_brand_where_clause(selected_brands: list[str]) -> str:
    conditions = [f"brands_tagged LIKE '%{escape_sql_literal(brand)}%'" for brand in selected_brands]
    return " AND ".join(conditions)


def build_brand_accounts_query(selected_brands: list[str]) -> str:
    where_clause = build_brand_where_clause(selected_brands)
    return f"""
        SELECT
            insta_id,
            tagged_account_count,
            brands_tagged
        FROM fsh.mart.cross_brand_accounts
        WHERE {where_clause}
        ORDER BY insta_id DESC;
    """


def build_brand_overall_query(selected_brands: list[str]) -> str:
    where_clause = build_brand_where_clause(selected_brands)
    excluded_brands = "', '".join(escape_sql_literal(brand) for brand in selected_brands)
    return f"""
        WITH selected_brand_accounts AS (
            SELECT
                insta_id
            FROM fsh.mart.cross_brand_accounts
            WHERE {where_clause}
        ),
        brand_list AS (
            SELECT DISTINCT
                insta_id,
                tagged_account
            FROM fsh.stage.group_by_tagged_post
            GROUP BY insta_id, tagged_account
        ),
        result AS (
            SELECT
                b.tagged_account AS TAGGED_ACCOUNT,
                COUNT(DISTINCT b.insta_id) AS UNIQUE_ACCOUNTS,
                COUNT(*) AS TOTAL_POSTS
            FROM brand_list b
            INNER JOIN selected_brand_accounts s
                ON b.insta_id = s.insta_id
            GROUP BY b.tagged_account
        )
        SELECT *
        FROM result
        WHERE TAGGED_ACCOUNT NOT IN ('{excluded_brands}')
        ORDER BY unique_accounts DESC, total_posts DESC;
    """


def build_top_brand_summary(df_overall: pd.DataFrame, top_n: int = 10) -> str:
    if df_overall.empty:
        return "해당 브랜드와 같이 태그된 브랜드가 없습니다."

    summary_lines = []
    limit = min(top_n, len(df_overall))
    for idx in range(limit):
        brand_name = df_overall["TAGGED_ACCOUNT"].iloc[idx]
        unique_accounts = df_overall["UNIQUE_ACCOUNTS"].iloc[idx]
        summary_lines.append(f"{idx + 1}. {brand_name} (태그 한 계정 수: {unique_accounts:,})")
    return "\n".join(summary_lines)

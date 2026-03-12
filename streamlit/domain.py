from __future__ import annotations

from datetime import datetime

import pandas as pd


DEFAULT_SELECTED_BRANDS = ["amomento.co", "lemaire"]


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def extract_brand_options(brand_df: pd.DataFrame) -> list[str]:
    if brand_df.empty or "TAGGED_ACCOUNT" not in brand_df.columns:
        return []
    return brand_df["TAGGED_ACCOUNT"].dropna().tolist()


def build_brand_in_clause(selected_brands: list[str]) -> str:
    escaped = [f"'{escape_sql_literal(brand)}'" for brand in selected_brands]
    return ", ".join(escaped)


def build_selected_brand_accounts_cte(selected_brands: list[str]) -> str:
    brand_in_clause = build_brand_in_clause(selected_brands)
    required_brand_count = len(selected_brands)
    return f"""
        WITH selected_brand_accounts AS (
            SELECT
                insta_id
            FROM fsh.mart.account_tagged_accounts
            WHERE tagged_account IN ({brand_in_clause})
            GROUP BY insta_id
            HAVING COUNT(DISTINCT tagged_account) = {required_brand_count}
        )
    """


def build_brand_accounts_query(selected_brands: list[str]) -> str:
    selected_brand_accounts_cte = build_selected_brand_accounts_cte(selected_brands)
    excluded_brands = "', '".join(escape_sql_literal(brand) for brand in selected_brands)
    selected_brand_in_clause = build_brand_in_clause(selected_brands)
    return f"""
        {selected_brand_accounts_cte},
        selected_brand_metrics AS (
            SELECT
                a.insta_id,
                COALESCE(MAX(NULLIF(a.insta_name, 'unknown')), 'unknown') AS insta_name,
                SUM(a.tagged_post_count) AS selected_brand_tag_post_count,
                LISTAGG(
                    a.tagged_account || ' ' || a.tagged_post_count || '개',
                    ' / '
                ) WITHIN GROUP (
                    ORDER BY a.tagged_post_count DESC, a.tagged_account
                ) AS selected_brand_tag_breakdown
            FROM fsh.mart.account_tagged_accounts a
            INNER JOIN selected_brand_accounts s
                ON a.insta_id = s.insta_id
            WHERE a.tagged_account IN ({selected_brand_in_clause})
            GROUP BY a.insta_id
        ),
        other_tagged_accounts AS (
            SELECT
                a.insta_id,
                COUNT(*) AS other_tagged_account_count,
                LISTAGG(
                    a.tagged_account || ' (' || a.tagged_post_count || '회)',
                    ', '
                ) WITHIN GROUP (
                    ORDER BY a.tagged_post_count DESC, a.tagged_account
                ) AS other_tagged_accounts_summary
            FROM fsh.mart.account_tagged_accounts a
            INNER JOIN selected_brand_accounts s
                ON a.insta_id = s.insta_id
            WHERE a.tagged_account NOT IN ('{excluded_brands}')
            GROUP BY a.insta_id
        ),
        all_tagged_accounts AS (
            SELECT
                insta_id,
                COUNT(*) AS total_tagged_account_count,
                LISTAGG(tagged_account, ', ')
                    WITHIN GROUP (ORDER BY tagged_account) AS brands_tagged,
                MAX(last_tagged_date) AS latest_related_date
            FROM fsh.mart.account_tagged_accounts
            GROUP BY insta_id
        )
        SELECT
            sbm.insta_id,
            sbm.insta_name,
            sbm.selected_brand_tag_post_count,
            sbm.selected_brand_tag_breakdown,
            ata.total_tagged_account_count,
            ata.brands_tagged,
            COALESCE(o.other_tagged_account_count, 0) AS other_tagged_account_count,
            COALESCE(o.other_tagged_accounts_summary, '-') AS other_tagged_accounts_summary,
            ata.latest_related_date
        FROM selected_brand_metrics sbm
        LEFT JOIN other_tagged_accounts o
            ON sbm.insta_id = o.insta_id
        LEFT JOIN all_tagged_accounts ata
            ON sbm.insta_id = ata.insta_id
        ORDER BY sbm.selected_brand_tag_post_count DESC, ata.latest_related_date DESC, sbm.insta_id ASC;
    """


def build_brand_overall_query(selected_brands: list[str]) -> str:
    selected_brand_accounts_cte = build_selected_brand_accounts_cte(selected_brands)
    excluded_brands = "', '".join(escape_sql_literal(brand) for brand in selected_brands)
    return f"""
        {selected_brand_accounts_cte},
        result AS (
            SELECT
                a.tagged_account AS TAGGED_ACCOUNT,
                COUNT(DISTINCT a.insta_id) AS ACCOUNT_COUNT,
                SUM(a.tagged_post_count) AS TAGGED_POST_TOTAL
            FROM fsh.mart.account_tagged_accounts a
            INNER JOIN selected_brand_accounts s
                ON a.insta_id = s.insta_id
            WHERE a.tagged_account NOT IN ('{excluded_brands}')
            GROUP BY a.tagged_account
        )
        SELECT *
        FROM result
        ORDER BY ACCOUNT_COUNT DESC, TAGGED_POST_TOTAL DESC, TAGGED_ACCOUNT ASC;
    """


def build_data_freshness_query() -> str:
    return """
        SELECT
            MAX(last_seen_at) AS LAST_LOADED_AT,
            MAX(post_date) AS LATEST_POST_DATE
        FROM fsh.raw_data.instagram_posts;
    """


def build_account_post_details_query(selected_brands: list[str]) -> str:
    selected_brand_accounts_cte = build_selected_brand_accounts_cte(selected_brands)
    return f"""
        {selected_brand_accounts_cte}
        SELECT
            r.insta_id,
            COALESCE(NULLIF(r.insta_name, ''), 'unknown') AS insta_name,
            r.post_id,
            r.post_date,
            COALESCE(NULLIF(r.tagged_insta_id, ''), '-') AS tagged_accounts,
            COALESCE(NULLIF(r.full_link, ''), '-') AS full_link
        FROM fsh.raw_data.instagram_posts r
        INNER JOIN selected_brand_accounts s
            ON r.insta_id = s.insta_id
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY r.post_id
            ORDER BY r.post_date DESC, r.last_seen_at DESC
        ) = 1
        ORDER BY r.insta_id, r.post_date DESC, r.post_id DESC;
    """


def summarize_kpis(
    selected_brands: list[str],
    df_accounts: pd.DataFrame,
    df_overall: pd.DataFrame,
) -> list[dict[str, str]]:
    total_accounts = len(df_accounts.index)
    avg_selected_tag_count = 0.0
    if not df_accounts.empty and "SELECTED_BRAND_TAG_POST_COUNT" in df_accounts.columns:
        avg_selected_tag_count = float(df_accounts["SELECTED_BRAND_TAG_POST_COUNT"].mean())

    if df_overall.empty:
        top_brand = "없음"
        top_brand_accounts = "0"
    else:
        top_brand = str(df_overall["TAGGED_ACCOUNT"].iloc[0])
        top_brand_accounts = f"{int(df_overall['ACCOUNT_COUNT'].iloc[0]):,}명"

    selected_label = " · ".join(selected_brands)
    return [
        {
            "label": "공통 태그 계정 수",
            "value": f"{total_accounts:,}개",
            "note": f"{selected_label}를 모두 함께 태그한 계정",
        },
        {
            "label": "계정당 평균 선택 태그",
            "value": f"{avg_selected_tag_count:.1f}회",
            "note": "공통 계정 1개당 평균 선택 브랜드 태그 횟수",
        },
        {
            "label": "가장 많이 함께 등장한 브랜드",
            "value": top_brand,
            "note": f"{top_brand_accounts} 계정에서 함께 등장",
        },
    ]


def prepare_accounts_table(df_accounts: pd.DataFrame) -> pd.DataFrame:
    if df_accounts.empty:
        return df_accounts

    prepared = df_accounts.copy()
    prepared["PROFILE_LINK"] = prepared["INSTA_ID"].apply(
        lambda value: f"https://www.instagram.com/{value}/" if value and value != "unknown" else "-"
    )
    prepared["LATEST_RELATED_DATE"] = prepared["LATEST_RELATED_DATE"].apply(_format_date_value)

    renamed = prepared.rename(
        columns={
            "INSTA_ID": "작성자 아이디",
            "INSTA_NAME": "프로필 이름",
            "SELECTED_BRAND_TAG_POST_COUNT": "선택 브랜드 총 태그 수",
            "SELECTED_BRAND_TAG_BREAKDOWN": "선택 브랜드 태그 상세",
            "TOTAL_TAGGED_ACCOUNT_COUNT": "전체 태그 계정 수",
            "BRANDS_TAGGED": "전체 함께 태그한 계정 목록",
            "OTHER_TAGGED_ACCOUNT_COUNT": "선택 브랜드 외 태그 계정 수",
            "OTHER_TAGGED_ACCOUNTS_SUMMARY": "선택 브랜드 외 태그 계정(횟수)",
            "LATEST_RELATED_DATE": "최근 게시물 날짜",
            "PROFILE_LINK": "프로필 링크",
        }
    ).copy()

    renamed["전체 함께 태그한 계정 목록"] = renamed["전체 함께 태그한 계정 목록"].apply(_truncate_account_list)
    renamed["선택 브랜드 외 태그 계정(횟수)"] = renamed["선택 브랜드 외 태그 계정(횟수)"].apply(
        lambda value: _truncate_account_list(value, limit=84)
    )
    return renamed[
        [
            "작성자 아이디",
            "프로필 이름",
            "선택 브랜드 총 태그 수",
            "최근 게시물 날짜",
            "프로필 링크",
        ]
    ]


def _truncate_account_list(value: object, limit: int = 56) -> str:
    if value is None:
        return "-"
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(", ") + "..."


def format_data_freshness(df_freshness: pd.DataFrame) -> tuple[str, str]:
    if df_freshness.empty:
        return "-", "-"

    loaded_at = df_freshness.iloc[0].get("LAST_LOADED_AT")
    latest_post_date = df_freshness.iloc[0].get("LATEST_POST_DATE")

    loaded_at_text = "-"
    latest_post_date_text = "-"

    if pd.notna(loaded_at):
        loaded_at_text = pd.to_datetime(loaded_at).strftime("%Y-%m-%d %H:%M")
    if pd.notna(latest_post_date):
        latest_post_date_text = pd.to_datetime(latest_post_date).strftime("%Y-%m-%d")

    return loaded_at_text, latest_post_date_text


def build_data_status(last_loaded_at: str, latest_post_date: str) -> dict[str, str]:
    if last_loaded_at == "-" or latest_post_date == "-":
        return {
            "label": "데이터 없음",
            "tone": "neutral",
            "description": "아직 적재된 데이터가 없습니다.",
        }

    loaded_at = pd.to_datetime(last_loaded_at)
    latest_date = pd.to_datetime(latest_post_date).date()
    now = datetime.now()
    hours_since_load = (now - loaded_at.to_pydatetime()).total_seconds() / 3600
    days_since_post = (now.date() - latest_date).days

    if hours_since_load <= 12 and days_since_post <= 1:
        return {
            "label": "정상",
            "tone": "healthy",
            "description": "최근 적재 기준으로 최신 상태에 가깝습니다.",
        }
    if hours_since_load <= 24 and days_since_post <= 2:
        return {
            "label": "주의",
            "tone": "watch",
            "description": "데이터가 약간 지연되었을 수 있습니다.",
        }
    return {
        "label": "지연",
        "tone": "stale",
        "description": "마지막 적재 시각 또는 최신 게시물 기준일이 오래되었습니다.",
    }


def build_header_context(
    selected_brands: list[str],
    last_loaded_at: str,
    latest_post_date: str,
) -> dict[str, object]:
    return {
        "selected_brands": selected_brands,
        "selected_brand_text": " · ".join(selected_brands),
        "analysis_rule": f"선택한 {len(selected_brands)}개 브랜드를 모두 함께 태그한 계정 기준",
        "last_loaded_at": last_loaded_at,
        "latest_post_date": latest_post_date,
        "status": build_data_status(last_loaded_at, latest_post_date),
    }


def build_top_brand_summary(df_overall: pd.DataFrame, top_n: int = 10) -> str:
    if df_overall.empty:
        return "해당 브랜드와 같이 태그된 브랜드가 없습니다."

    summary_lines = []
    limit = min(top_n, len(df_overall))
    for idx in range(limit):
        brand_name = df_overall["TAGGED_ACCOUNT"].iloc[idx]
        account_count = df_overall["ACCOUNT_COUNT"].iloc[idx]
        summary_lines.append(f"{idx + 1}. {brand_name} (태그한 계정 수: {account_count:,})")
    return "\n".join(summary_lines)


def prepare_top_accounts_snapshot(df_accounts: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df_accounts.empty:
        return df_accounts

    snapshot = df_accounts.head(top_n).copy()
    snapshot["DISPLAY_NAME"] = snapshot["INSTA_NAME"].where(
        snapshot["INSTA_NAME"].fillna("unknown").ne("unknown"),
        snapshot["INSTA_ID"],
    )
    snapshot["PROFILE_LINK"] = snapshot["INSTA_ID"].apply(
        lambda value: f"https://www.instagram.com/{value}/" if value and value != "unknown" else "-"
    )

    return snapshot.rename(
        columns={
            "DISPLAY_NAME": "프로필 이름",
            "INSTA_ID": "작성자 아이디",
            "SELECTED_BRAND_TAG_POST_COUNT": "선택 브랜드 총 태그 수",
            "SELECTED_BRAND_TAG_BREAKDOWN": "선택 브랜드 태그 상세",
            "LATEST_RELATED_DATE": "최근 게시물 날짜",
            "PROFILE_LINK": "프로필 링크",
        }
    )[
        ["프로필 이름", "작성자 아이디", "선택 브랜드 총 태그 수", "선택 브랜드 태그 상세", "최근 게시물 날짜", "프로필 링크"]
    ]


def build_first_tab_insight(df_accounts: pd.DataFrame, df_overall: pd.DataFrame) -> str:
    if df_accounts.empty:
        return "선택한 브랜드를 함께 태그한 계정이 아직 없습니다."

    top_account = df_accounts.iloc[0]
    top_account_name = top_account.get("INSTA_NAME")
    top_account_id = top_account.get("INSTA_ID")
    account_label = top_account_name if pd.notna(top_account_name) and top_account_name != "unknown" else top_account_id
    selected_tag_count = int(top_account.get("SELECTED_BRAND_TAG_POST_COUNT", 0))
    selected_tag_breakdown = top_account.get("SELECTED_BRAND_TAG_BREAKDOWN") or "-"

    if df_overall.empty:
        return (
            f"현재 선택 조합에서 가장 많이 선택 브랜드를 태그한 계정은 {account_label}이며, "
            f"총 {selected_tag_count}회 태그했습니다 ({selected_tag_breakdown}). "
            f"함께 등장한 추가 브랜드 데이터는 아직 없습니다."
        )

    top_brand = df_overall.iloc[0]["TAGGED_ACCOUNT"]
    top_brand_accounts = int(df_overall.iloc[0]["ACCOUNT_COUNT"])
    return (
        f"현재 선택 조합에서 가장 많이 선택 브랜드를 태그한 계정은 {account_label}이며 "
        f"총 {selected_tag_count}회 태그했습니다 ({selected_tag_breakdown}). "
        f"함께 가장 넓게 등장한 브랜드는 {top_brand}로, {top_brand_accounts}개 계정에서 확인됩니다."
    )


def _format_date_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return pd.to_datetime(value).strftime("%Y-%m-%d")

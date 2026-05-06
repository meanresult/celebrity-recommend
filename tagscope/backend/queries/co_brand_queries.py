from __future__ import annotations

from .tagger_queries import _escape, _in_clause, _selected_brand_accounts_cte


def build_co_brand_kpi_query(brands: list[str]) -> str:
    excluded = _in_clause(brands)
    return f"""
    WITH {_selected_brand_accounts_cte(brands)},
    tagger_count AS (
        SELECT COUNT(*) AS total_accounts FROM selected_brand_accounts
    ),
    co_brand_count AS (
        SELECT COUNT(DISTINCT tagged_account) AS co_brand_count
        FROM MART.account_tagged_accounts a
        INNER JOIN selected_brand_accounts s ON a.insta_id = s.insta_id
        WHERE a.tagged_account NOT IN ({excluded})
    )
    SELECT t.total_accounts, c.co_brand_count
    FROM tagger_count t, co_brand_count c
    """


def build_co_brand_ranking_query(brands: list[str]) -> str:
    excluded = _in_clause(brands)
    return f"""
    WITH {_selected_brand_accounts_cte(brands)},
    total AS (
        SELECT COUNT(*) AS total FROM selected_brand_accounts
    ),
    ranked AS (
        SELECT
            a.tagged_account,
            COUNT(DISTINCT a.insta_id) AS tagger_count,
            SUM(a.tagged_post_count) AS total_tag_count
        FROM MART.account_tagged_accounts a
        INNER JOIN selected_brand_accounts s ON a.insta_id = s.insta_id
        WHERE a.tagged_account NOT IN ({excluded})
        GROUP BY a.tagged_account
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY tagger_count DESC, total_tag_count DESC) AS rank,
        r.tagged_account,
        r.tagger_count,
        r.total_tag_count,
        ROUND(r.tagger_count * 100.0 / t.total, 1) AS tagger_ratio
    FROM ranked r, total t
    ORDER BY tagger_count DESC, total_tag_count DESC
    """


def build_co_brand_detail_query(tagged_account: str, brands: list[str]) -> str:
    escaped_account = _escape(tagged_account)
    excluded = _in_clause(brands)
    return f"""
    WITH {_selected_brand_accounts_cte(brands)},
    taggers AS (
        SELECT
            a.insta_id,
            COALESCE(MAX(NULLIF(a.insta_name, 'unknown')), a.insta_id) AS display_name,
            sub.tag_count,
            sub.latest_tag_date
        FROM MART.account_tagged_accounts a
        INNER JOIN selected_brand_accounts s ON a.insta_id = s.insta_id
        INNER JOIN (
            SELECT insta_id,
                   SUM(tagged_post_count) AS tag_count,
                   MAX(last_tagged_date) AS latest_tag_date
            FROM MART.account_tagged_accounts
            WHERE tagged_account = '{escaped_account}'
            GROUP BY insta_id
        ) sub ON a.insta_id = sub.insta_id
        WHERE a.tagged_account IN ({excluded})
        GROUP BY a.insta_id, sub.tag_count, sub.latest_tag_date
        ORDER BY sub.tag_count DESC
        LIMIT 50
    ),
    monthly AS (
        SELECT
            date_trunc('month', g.post_date)::date AS month,
            COUNT(DISTINCT g.insta_id) AS tagger_count
        FROM STAGE.group_by_tagged_post g
        INNER JOIN selected_brand_accounts s ON g.insta_id = s.insta_id
        WHERE g.tagged_account = '{escaped_account}'
        GROUP BY date_trunc('month', g.post_date)::date
        ORDER BY month
    )
    SELECT
        'taggers' AS section,
        to_json(list({{
            'insta_id': insta_id,
            'display_name': display_name,
            'tag_count': tag_count,
            'latest_tag_date': latest_tag_date::varchar
        }})) AS data
    FROM taggers
    UNION ALL
    SELECT
        'monthly',
        to_json(list({{
            'month': month::varchar,
            'tagger_count': tagger_count
        }}))
    FROM monthly
    """

from __future__ import annotations


def _escape(value: str) -> str:
    return value.replace("'", "''")


def _in_clause(brands: list[str]) -> str:
    return ", ".join(f"'{_escape(b)}'" for b in brands)


def _selected_brand_accounts_cte(brands: list[str]) -> str:
    return f"""
    selected_brand_accounts AS (
        SELECT insta_id
        FROM MART.account_tagged_accounts
        WHERE tagged_account IN ({_in_clause(brands)})
        GROUP BY insta_id
        HAVING COUNT(DISTINCT tagged_account) = {len(brands)}
    )"""


def build_tagger_kpi_query(brands: list[str]) -> str:
    return f"""
    WITH {_selected_brand_accounts_cte(brands)},
    metrics AS (
        SELECT
            COUNT(DISTINCT s.insta_id) AS total_accounts,
            COALESCE(AVG(sub.tag_count), 0) AS avg_tag_count
        FROM selected_brand_accounts s
        LEFT JOIN (
            SELECT insta_id, SUM(tagged_post_count) AS tag_count
            FROM MART.account_tagged_accounts
            WHERE tagged_account IN ({_in_clause(brands)})
            GROUP BY insta_id
        ) sub ON s.insta_id = sub.insta_id
    ),
    top_tagger AS (
        SELECT
            a.insta_id,
            COALESCE(MAX(NULLIF(a.insta_name, 'unknown')), a.insta_id) AS display_name,
            SUM(a.tagged_post_count) AS tag_count
        FROM MART.account_tagged_accounts a
        INNER JOIN selected_brand_accounts s ON a.insta_id = s.insta_id
        WHERE a.tagged_account IN ({_in_clause(brands)})
        GROUP BY a.insta_id
        ORDER BY tag_count DESC
        LIMIT 1
    )
    SELECT
        m.total_accounts,
        ROUND(m.avg_tag_count, 1) AS avg_tag_count,
        t.insta_id AS top_tagger_id,
        t.display_name AS top_tagger_name,
        t.tag_count AS top_tagger_count
    FROM metrics m
    LEFT JOIN top_tagger t ON true
    """


def build_tagger_list_query(brands: list[str], limit: int, offset: int) -> str:
    excluded = _in_clause(brands)
    return f"""
    WITH {_selected_brand_accounts_cte(brands)},
    ranked AS (
        SELECT
            a.insta_id,
            COALESCE(MAX(NULLIF(a.insta_name, 'unknown')), a.insta_id) AS insta_name,
            SUM(a.tagged_post_count) AS tag_count,
            MAX(a.last_tagged_date) AS latest_tag_date,
            COUNT(DISTINCT ot.tagged_account) AS other_brand_count
        FROM MART.account_tagged_accounts a
        INNER JOIN selected_brand_accounts s ON a.insta_id = s.insta_id
        LEFT JOIN MART.account_tagged_accounts ot
            ON ot.insta_id = a.insta_id
            AND ot.tagged_account NOT IN ({excluded})
        WHERE a.tagged_account IN ({excluded})
        GROUP BY a.insta_id
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY tag_count DESC, latest_tag_date DESC) AS rank,
        insta_id,
        insta_name,
        tag_count,
        latest_tag_date,
        other_brand_count
    FROM ranked
    ORDER BY tag_count DESC, latest_tag_date DESC
    LIMIT {limit} OFFSET {offset}
    """


def build_tagger_count_query(brands: list[str]) -> str:
    return f"""
    WITH {_selected_brand_accounts_cte(brands)}
    SELECT COUNT(*) AS total FROM selected_brand_accounts
    """


def build_tagger_detail_query(insta_id: str, brands: list[str]) -> str:
    escaped_id = _escape(insta_id)
    excluded = _in_clause(brands)
    return f"""
    WITH top_brands AS (
        SELECT tagged_account, tagged_post_count
        FROM MART.account_tagged_accounts
        WHERE insta_id = '{escaped_id}'
          AND tagged_account NOT IN ({excluded})
        ORDER BY tagged_post_count DESC
        LIMIT 10
    ),
    recent_posts AS (
        SELECT
            post_id,
            post_date,
            COALESCE(NULLIF(tagged_insta_id, ''), '-') AS tagged_accounts,
            COALESCE(NULLIF(full_link, ''), '') AS full_link
        FROM RAW_DATA.INSTAGRAM_POSTS
        WHERE insta_id = '{escaped_id}'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY post_id ORDER BY post_date DESC, last_seen_at DESC
        ) = 1
        ORDER BY post_date DESC
        LIMIT 10
    ),
    profile AS (
        SELECT
            insta_id,
            COALESCE(MAX(NULLIF(insta_name, 'unknown')), '{escaped_id}') AS display_name
        FROM MART.account_tagged_accounts
        WHERE insta_id = '{escaped_id}'
        GROUP BY insta_id
    )
    SELECT 'profile' AS section, to_json({{
        'insta_id': p.insta_id,
        'display_name': p.display_name
    }}) AS data
    FROM profile p
    UNION ALL
    SELECT 'top_brands', to_json(list({{
        'brand': tagged_account,
        'count': tagged_post_count
    }}))
    FROM top_brands
    UNION ALL
    SELECT 'recent_posts', to_json(list({{
        'post_id': post_id,
        'post_date': post_date::varchar,
        'tagged_accounts': tagged_accounts,
        'full_link': full_link
    }}))
    FROM recent_posts
    """

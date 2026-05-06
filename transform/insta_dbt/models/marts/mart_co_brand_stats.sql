{{
  config(
    materialized='table'
  )
}}

-- 브랜드를 태그한 계정 수 / 총 태그 횟수 / 비율(%) 사전 집계
-- 비율: 해당 브랜드를 태그한 계정 수 / 전체 unique 계정 수
with total_accounts as (
    select count(distinct insta_id) as total
    from {{ ref('account_tagged_accounts') }}
),

brand_stats as (
    select
        tagged_account,
        count(distinct insta_id)  as tagger_count,
        sum(tagged_post_count)    as total_tag_count
    from {{ ref('account_tagged_accounts') }}
    group by tagged_account
)

select
    b.tagged_account,
    b.tagger_count,
    b.total_tag_count,
    round(b.tagger_count * 100.0 / t.total, 1) as tagger_ratio
from brand_stats b
cross join total_accounts t

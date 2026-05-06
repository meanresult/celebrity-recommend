{{
  config(
    materialized='table'
  )
}}

select
    tagged_account,
    date_trunc('month', post_date)::date as month,
    count(distinct insta_id)             as unique_tagger_count,
    count(distinct post_id)              as post_count
from {{ ref('group_by_tagged_post') }}
group by tagged_account, date_trunc('month', post_date)::date

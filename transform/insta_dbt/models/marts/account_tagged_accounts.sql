{{
  config(
    materialized='table'
  )
}}

select
    insta_id,
    coalesce(max(nullif(insta_name, 'unknown')), 'unknown') as insta_name,
    tagged_account,
    min(post_date) as first_tagged_date,
    max(post_date) as last_tagged_date,
    count(distinct post_id) as tagged_post_count
from {{ ref('group_by_tagged_post') }}
group by insta_id, tagged_account

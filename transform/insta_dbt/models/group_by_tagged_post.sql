{{config(materialized='view')}}
with base as (
    select
        post_id
        ,insta_id
        ,brand_name
        ,brand_id
        ,post_date
        ,tagged_insta_id
        ,tagged_insta_id_cnt
    
    from {{ source('instagram_raw', 'instagram_posts') }}
    where tagged_insta_id is not null
      and trim(tagged_insta_id) <> ''
),
-- 쉼표 기준으로 나누기 
split as (
    select
        post_id
        ,insta_id
        ,brand_name
        ,brand_id
        ,post_date
        ,tagged_insta_id_cnt
        ,split(tagged_insta_id, ',') as tag_arr
    from base
),

flattened as (
    select
        post_id
        ,insta_id
        ,brand_name
        ,brand_id
        ,post_date
        ,f.index + 1 as tag_pos
        ,trim(f.value::string) as tagged_account_raw
    from split,
    lateral flatten(input => tag_arr) f
),

clean as (
  select
    tag_pos,
    post_id,
    insta_id,
    brand_name,
    brand_id,
    post_date,
    -- 정제: 공백 제거 + 앞의 @ 제거
    lower(
      rtrim(
          regexp_replace(tagged_account_raw, '^@', ''),
          '.'
      )
    ) as tagged_account
  from flattened
  where tagged_account_raw is not null
    and tagged_account_raw <> ''
),

final as (
    select
        md5(
            concat_ws(
                '||',
                post_id,
                tag_pos::string,
                tagged_account
            )
        ) as pk_tagged_post,
        tag_pos,
        post_id,
        insta_id,
        brand_name,
        brand_id,
        post_date,
        tagged_account
    from clean
)

select * from final

{{config(materialized='view')}}
with base as (
    select
        post_id
        ,insta_id
        ,insta_name
        ,brand_name
        ,brand_id
        ,post_date
        ,full_link
        ,tagged_insta_id
        ,tagged_insta_id_cnt

    from {{ source('instagram_raw', 'instagram_posts') }}
    where tagged_insta_id is not null
      and trim(tagged_insta_id) <> ''
),
split as (
    select
        post_id
        ,insta_id
        ,insta_name
        ,brand_name
        ,brand_id
        ,post_date
        ,full_link
        ,tagged_insta_id_cnt
        ,string_split(tagged_insta_id, ',') as tag_arr
    from base
),

flattened as (
    select
        post_id
        ,insta_id
        ,insta_name
        ,brand_name
        ,brand_id
        ,post_date
        ,full_link
        ,tag_pos
        ,trim(tagged_account_raw) as tagged_account_raw
    from split
    cross join unnest(tag_arr) with ordinality as t(tagged_account_raw, tag_pos)
),

clean as (
  select
    tag_pos,
    post_id,
    insta_id,
    insta_name,
    brand_name,
    brand_id,
    post_date,
    full_link,
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
                tag_pos::varchar,
                tagged_account
            )
        ) as pk_tagged_post,
        tag_pos,
        post_id,
        insta_id,
        insta_name,
        brand_name,
        brand_id,
        post_date,
        full_link,
        tagged_account
    from clean
)

select * from final

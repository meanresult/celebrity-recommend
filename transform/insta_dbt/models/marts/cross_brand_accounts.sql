{{
  config(
    materialized='table'
  )
}}

-- 계정별 태그한 브랜드 집계
SELECT 
    insta_id,
    COUNT(DISTINCT tagged_account) as brand_count,
    LISTAGG(DISTINCT tagged_account, ', ') 
        WITHIN GROUP (ORDER BY tagged_account) as brands_tagged
FROM {{ ref('group_by_tagged_post') }}
GROUP BY insta_id
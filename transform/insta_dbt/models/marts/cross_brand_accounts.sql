{{
  config(
    materialized='table'
  )
}}

-- 계정별 태그한 브랜드 집계
SELECT 
    insta_id,
    coalesce(max(nullif(insta_name, 'unknown')), 'unknown') as insta_name,
    COUNT(*) as tagged_account_count,
    LISTAGG(tagged_account, ', ') 
        WITHIN GROUP (ORDER BY tagged_account) as brands_tagged
FROM {{ ref('account_tagged_accounts') }}
GROUP BY insta_id

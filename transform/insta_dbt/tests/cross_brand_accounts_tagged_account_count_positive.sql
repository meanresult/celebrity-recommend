select *
from {{ ref('cross_brand_accounts') }}
where tagged_account_count < 1

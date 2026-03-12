select
    insta_id,
    tagged_account,
    count(*) as row_count
from {{ ref('account_tagged_accounts') }}
group by insta_id, tagged_account
having count(*) > 1

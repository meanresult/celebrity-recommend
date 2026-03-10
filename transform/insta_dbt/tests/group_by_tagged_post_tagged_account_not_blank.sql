select *
from {{ ref('group_by_tagged_post') }}
where trim(tagged_account) = ''

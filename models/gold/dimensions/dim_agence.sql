select
    branch_id       as agence_id,
    branch_code     as code_agence,
    branch_name     as agence,
    city            as ville,
    postal_code     as code_postal,
    opened_on       as date_ouverture
from {{ ref('silver_branches') }}

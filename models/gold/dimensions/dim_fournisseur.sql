select
    supplier_id                 as fournisseur_id,
    supplier_name               as fournisseur,
    country_code                as pays,
    standard_lead_time_days     as delai_standard_jours
from {{ ref('silver_suppliers') }}

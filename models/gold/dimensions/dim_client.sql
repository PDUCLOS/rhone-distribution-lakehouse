-- Every customer is kept: dropping an incomplete record would silently drop its
-- revenue from every report. The defect is flagged (and listed in silver_quarantine).
select
    customer_id             as client_id,
    account_code            as code_client,
    company_name            as raison_sociale,
    segment,
    naf_code                as code_naf,
    size_band               as tranche_effectif,
    city                    as ville,
    postal_code             as code_postal,
    departement,
    contact_name            as contact_nom,
    contact_email,
    contact_phone           as contact_telephone,
    payment_terms_days      as delai_paiement_jours,
    credit_limit            as limite_credit,
    branch_id               as agence_id,
    rep_id                  as commercial_id,
    created_on              as date_creation,
    is_missing_postal_code  as code_postal_manquant
from {{ ref('silver_customers') }}

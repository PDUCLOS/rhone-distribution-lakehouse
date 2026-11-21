-- =============================================================================
-- Show the regulated access at work (run after dbt build --target snowflake).
-- Same three queries, five roles. Expected results in the comments.
-- =============================================================================

-- Demo hygiene: only the primary role counts (the policies use current_role()).
use secondary roles none;
use warehouse rd_wh;

-- DAF: 5 agencies, real e-mails, margins visible
use role rd_daf;
select count(distinct agence_id) as agences_visibles, sum(ca_net) as ca, sum(marge_brute) as marge from rhone.gold.fct_ventes_jour;
select raison_sociale, contact_email, limite_credit from rhone.gold.dim_client limit 3;

-- Sales direction: 5 agencies, margins visible, e-mails masked (*****@...)
use role rd_direction_commerciale;
select count(distinct agence_id) as agences_visibles, sum(ca_net) as ca, sum(marge_brute) as marge from rhone.gold.fct_ventes_jour;
select raison_sociale, contact_email, limite_credit from rhone.gold.dim_client limit 3;

-- Analyst: 5 agencies, margin NULL, e-mails masked
use role rd_analyste;
select count(distinct agence_id) as agences_visibles, sum(ca_net) as ca, sum(marge_brute) as marge from rhone.gold.fct_ventes_jour;
select raison_sociale, contact_email, limite_credit from rhone.gold.dim_client limit 3;

-- Sales rep Lyon Gerland: ONE agency (1), margin NULL, e-mails visible
use role rd_commercial_lyg;
select count(distinct agence_id) as agences_visibles, sum(ca_net) as ca, sum(marge_brute) as marge from rhone.gold.fct_ventes_jour;
select raison_sociale, contact_email, limite_credit from rhone.gold.dim_client limit 3;

-- Sales rep Saint-Étienne: ONE agency (5), different customers
use role rd_commercial_ste;
select count(distinct agence_id) as agences_visibles, sum(ca_net) as ca from rhone.gold.fct_ventes_jour;

-- Who can see what, from the catalog
use role sysadmin;
select *
from table(rhone.information_schema.policy_references(ref_entity_name => 'rhone.gold.dim_client', ref_entity_domain => 'table'));

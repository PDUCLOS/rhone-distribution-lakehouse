-- DSO by month and branch: receivables at month end / revenue (incl. VAT) of the last 90 days x 90.
with months as (
    select distinct debut_mois as mois
    from {{ ref('dim_date') }}
),

month_ends as (
    select mois, {{ dbt.dateadd('day', -1, dbt.dateadd('month', 1, 'mois')) }} as fin_mois
    from months
),

factures as (
    select * from {{ ref('fct_factures') }}
),

per_month as (
    select
        month_ends.mois,
        factures.agence_id,
        sum(case
                when factures.date_facture <= month_ends.fin_mois
                 and (factures.date_paiement is null or factures.date_paiement > month_ends.fin_mois)
                then factures.montant_ttc else 0 end)                       as encours_fin_mois,
        sum(case
                when factures.date_facture >  {{ dbt.dateadd('day', -90, 'month_ends.fin_mois') }}
                 and factures.date_facture <= month_ends.fin_mois
                then factures.montant_ttc else 0 end)                       as ca_ttc_90j
    from month_ends
    cross join factures
    group by 1, 2
)

select
    mois,
    agence_id,
    encours_fin_mois,
    ca_ttc_90j,
    round(encours_fin_mois / nullif(ca_ttc_90j, 0) * 90, 1) as dso_jours
from per_month
where ca_ttc_90j > 0

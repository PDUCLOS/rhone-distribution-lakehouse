-- Aged receivables at the latest invoice date, per customer (DAF).
-- Open credit notes (negative) are netted against the customer's balance.
with open_items as (
    select *
    from {{ ref('fct_factures') }}
    where reste_a_payer <> 0
)

select
    client_id,
    agence_id,
    count(*)                                                                        as nb_factures_ouvertes,
    sum(reste_a_payer)                                                              as encours_ttc,
    sum(case when jours_retard <= 0 then reste_a_payer else 0 end)                  as non_echu,
    sum(case when jours_retard between 1 and 30 then reste_a_payer else 0 end)      as retard_1_30,
    sum(case when jours_retard between 31 and 60 then reste_a_payer else 0 end)     as retard_31_60,
    sum(case when jours_retard between 61 and 90 then reste_a_payer else 0 end)     as retard_61_90,
    sum(case when jours_retard > 90 then reste_a_payer else 0 end)                  as retard_plus_90,
    max(jours_retard)                                                               as retard_max_jours
from open_items
group by client_id, agence_id

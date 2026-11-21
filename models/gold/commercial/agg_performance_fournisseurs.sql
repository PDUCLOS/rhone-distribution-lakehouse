-- Supplier delivery performance on received purchase orders.
with po as (
    select * from {{ ref('silver_purchase_orders') }}
    where received_on is not null
)

select
    {{ dbt.date_trunc('month', 'po.ordered_on') }}                           as mois,
    po.supplier_id                                                           as fournisseur_id,
    count(*)                                                                 as nb_commandes_achat,
    avg({{ dbt.datediff('po.ordered_on', 'po.received_on', 'day') }})        as delai_moyen_jours,
    avg({{ dbt.datediff('po.expected_on', 'po.received_on', 'day') }})       as retard_moyen_jours,
    avg(case when po.received_on <= po.expected_on then 1.0 else 0.0 end)    as taux_a_l_heure,
    sum(po.qty_ordered * po.unit_cost)                                       as montant_achats
from po
group by 1, 2

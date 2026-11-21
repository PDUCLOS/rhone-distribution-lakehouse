-- Monthly snapshot per customer for the churn model.
-- Label: no order in the next `churn_horizon_days` days. Recent snapshots
-- whose horizon is not fully observed get a null label (score, don't train).
{% set horizon = var('churn_horizon_days') %}

with sales as (
    select client_id, date_vente, ca_net, nb_commandes
    from {{ ref('fct_ventes_jour') }}
),

invoices as (
    select client_id, date_facture, jours_retard
    from {{ ref('fct_factures') }}
),

snapshots as (
    select distinct {{ dbt.dateadd('day', -1, dbt.dateadd('month', 1, 'debut_mois')) }} as snapshot_date
    from {{ ref('dim_date') }}
),

bounds as (
    select max(date_vente) as last_observed from sales
),

grid as (
    select clients.client_id, snapshots.snapshot_date
    from {{ ref('dim_client') }} as clients
    cross join snapshots
    where snapshots.snapshot_date >= (select min(date_vente) from sales)
      and snapshots.snapshot_date <= (select last_observed from bounds)
),

features as (
    select
        grid.client_id,
        grid.snapshot_date,
        max(case when sales.date_vente <= grid.snapshot_date then sales.date_vente end)     as last_order_date,
        sum(case when sales.date_vente >  {{ dbt.dateadd('day', -90, 'grid.snapshot_date') }}
                  and sales.date_vente <= grid.snapshot_date then sales.nb_commandes else 0 end)  as orders_last_90d,
        sum(case when sales.date_vente >  {{ dbt.dateadd('day', -180, 'grid.snapshot_date') }}
                  and sales.date_vente <= {{ dbt.dateadd('day', -90, 'grid.snapshot_date') }}
                 then sales.nb_commandes else 0 end)                                         as orders_prev_90d,
        sum(case when sales.date_vente >  {{ dbt.dateadd('day', -90, 'grid.snapshot_date') }}
                  and sales.date_vente <= grid.snapshot_date then sales.ca_net else 0 end)       as revenue_last_90d,
        sum(case when sales.date_vente >  {{ dbt.dateadd('day', -180, 'grid.snapshot_date') }}
                  and sales.date_vente <= {{ dbt.dateadd('day', -90, 'grid.snapshot_date') }}
                 then sales.ca_net else 0 end)                                                as revenue_prev_90d,
        sum(case when sales.date_vente >  grid.snapshot_date
                  and sales.date_vente <= {{ dbt.dateadd('day', horizon, 'grid.snapshot_date') }}
                 then 1 else 0 end)                                                           as sales_rows_next_horizon
    from grid
    left join sales
        on sales.client_id = grid.client_id
       and sales.date_vente <= {{ dbt.dateadd('day', horizon, 'grid.snapshot_date') }}
    group by grid.client_id, grid.snapshot_date
),

payment_behaviour as (
    select
        grid.client_id,
        grid.snapshot_date,
        avg(invoices.jours_retard) as avg_days_late_last_90d
    from grid
    inner join invoices
        on invoices.client_id = grid.client_id
       and invoices.date_facture >  {{ dbt.dateadd('day', -90, 'grid.snapshot_date') }}
       and invoices.date_facture <= grid.snapshot_date
    group by grid.client_id, grid.snapshot_date
)

select
    features.client_id,
    features.snapshot_date                                                          as date_snapshot,
    {{ dbt.datediff('features.last_order_date', 'features.snapshot_date', 'day') }} as jours_depuis_derniere_commande,
    features.orders_last_90d                                                        as nb_commandes_90j,
    features.orders_prev_90d                                                        as nb_commandes_90j_precedents,
    features.revenue_last_90d                                                       as ca_90j,
    features.revenue_prev_90d                                                       as ca_90j_precedents,
    features.revenue_last_90d / nullif(features.orders_last_90d, 0)                 as panier_moyen_90j,
    payment_behaviour.avg_days_late_last_90d                                        as retard_paiement_moyen_90j,
    case
        when {{ dbt.dateadd('day', horizon, 'features.snapshot_date') }} > bounds.last_observed then null
        when features.sales_rows_next_horizon = 0 then 1
        else 0
    end                                                                             as label_churn
from features
cross join bounds
left join payment_behaviour
    on features.client_id = payment_behaviour.client_id
   and features.snapshot_date = payment_behaviour.snapshot_date
-- Only customers active in the previous 6 months can churn
where features.orders_last_90d + features.orders_prev_90d > 0

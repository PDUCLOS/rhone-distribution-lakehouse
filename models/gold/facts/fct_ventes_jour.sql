{{
    config(
        materialized='incremental',
        unique_key=['date_vente', 'client_id', 'produit_id', 'agence_id', 'commercial_id', 'canal'],
        on_schema_change='append_new_columns'
    )
}}

-- Grain: day x customer x product x branch x rep x channel (the nightly extract grain).
-- Incremental: only the last few days are recomputed, so the nightly run stays cheap.
-- Records in quarantine (pricing defects) are excluded.
with sales as (
    select * from {{ ref('silver_daily_sales') }}
    where not is_zero_price
      and not is_unflagged_negative_qty
    {% if is_incremental() %}
      and sale_date >= (
          select {{ dbt.dateadd('day', -var('incremental_lookback_days'), 'max(date_vente)') }}
          from {{ this }}
      )
    {% endif %}
),

customers as (
    select client_id from {{ ref('dim_client') }}
)

select
    sales.sale_date                                 as date_vente,
    sales.customer_id                               as client_id,
    sales.product_id                                as produit_id,
    sales.branch_id                                 as agence_id,
    sales.rep_id                                    as commercial_id,
    sales.channel                                   as canal,
    sales.order_count                               as nb_commandes,
    sales.line_count                                as nb_lignes,
    sales.qty_ordered                               as qte_commandee,
    sales.qty_shipped                               as qte_livree,
    sales.qty_returned                              as qte_retournee,
    sales.net_amount                                as ca_net,
    sales.cost_amount                               as cout_achat,
    sales.net_amount - sales.cost_amount            as marge_brute,
    sales.ordered_amount                            as montant_commande,
    sales.extracted_at                              as extrait_le
from sales
inner join customers
    on sales.customer_id = customers.client_id

-- Service level: share of ordered quantity actually shipped, by month, family and supplier.
select
    {{ dbt.date_trunc('month', 'ventes.date_vente') }}  as mois,
    ventes.agence_id,
    produits.famille,
    produits.fournisseur_id,
    sum(ventes.qte_commandee)                           as qte_commandee,
    sum(ventes.qte_livree)                              as qte_livree,
    cast(sum(ventes.qte_livree) as {{ dbt.type_float() }})
        / nullif(sum(ventes.qte_commandee), 0)          as taux_service
from {{ ref('fct_ventes_jour') }} as ventes
inner join {{ ref('dim_produit') }} as produits
    on ventes.produit_id = produits.produit_id
group by 1, 2, 3, 4

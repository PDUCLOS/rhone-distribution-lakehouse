-- Monthly revenue and gross margin by branch and product family (DAF / sales direction).
select
    {{ dbt.date_trunc('month', 'ventes.date_vente') }}  as mois,
    ventes.agence_id,
    produits.famille,
    sum(ventes.ca_net)                                  as ca_net,
    sum(ventes.marge_brute)                             as marge_brute,
    sum(ventes.marge_brute) / nullif(sum(ventes.ca_net), 0) as taux_marge,
    sum(ventes.nb_commandes)                            as nb_commandes,
    count(distinct ventes.client_id)                    as nb_clients_actifs
from {{ ref('fct_ventes_jour') }} as ventes
inner join {{ ref('dim_produit') }} as produits
    on ventes.produit_id = produits.produit_id
group by 1, 2, 3

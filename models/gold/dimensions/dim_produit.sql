select
    products.product_id         as produit_id,
    products.sku,
    products.product_name       as produit,
    products.product_family     as famille,
    products.sales_unit         as unite,
    products.supplier_id        as fournisseur_id,
    suppliers.supplier_name     as fournisseur,
    products.list_price_2024    as prix_catalogue_2024,
    products.unit_cost_2024     as cout_achat_2024
from {{ ref('silver_products') }} as products
inner join {{ ref('silver_suppliers') }} as suppliers
    on products.supplier_id = suppliers.supplier_id

-- Every record failing a business rule, one row per anomaly. Gold excludes
-- them; the data steward works from this table.
{% set rules = [
    ('zero_price_line', 'silver_daily_sales', "cast(sale_date as varchar) || '|' || cast(customer_id as varchar) || '|' || cast(product_id as varchar)", 'is_zero_price'),
    ('negative_qty_not_flagged_as_return', 'silver_daily_sales', "cast(sale_date as varchar) || '|' || cast(customer_id as varchar) || '|' || cast(product_id as varchar)", 'is_unflagged_negative_qty'),
    ('shipped_before_order', 'silver_shipments', 'cast(shipment_id as varchar)', 'is_shipped_before_order'),
    ('orphan_invoice', 'silver_invoices', 'cast(invoice_id as varchar)', 'is_orphan'),
    ('customer_missing_postal_code', 'silver_customers', 'cast(customer_id as varchar)', 'is_missing_postal_code'),
] %}

{% for anomaly_type, model_name, record_key, flag in rules %}
select
    '{{ anomaly_type }}'    as anomaly_type,
    '{{ model_name }}'      as source_model,
    {{ record_key }}        as record_key
from {{ ref(model_name) }}
where {{ flag }}
{% if not loop.last %}union all{% endif %}
{% endfor %}

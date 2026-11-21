with latest as (
    {{ latest_version(source('bronze', 'payments'), ['payment_id']) }}
)

select
    cast(payment_id as {{ dbt.type_bigint() }})     as payment_id,
    cast(invoice_id as {{ dbt.type_bigint() }})     as invoice_id,
    cast(paid_on as date)                           as paid_on,
    cast(amount_paid as {{ dbt.type_numeric() }})   as amount_paid,
    payment_method
from latest

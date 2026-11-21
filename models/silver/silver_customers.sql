with latest as (
    {{ latest_version(source('bronze', 'customers'), ['customer_id']) }}
)

select
    cast(customer_id as integer)                    as customer_id,
    cast(account_code as {{ dbt.type_string() }})   as account_code,
    company_name,
    segment,
    naf_code,
    size_band,
    city,
    cast(postal_code as {{ dbt.type_string() }})    as postal_code,
    left(cast(postal_code as {{ dbt.type_string() }}), 2) as departement,
    contact_name,
    contact_email,
    contact_phone,
    cast(payment_terms_days as integer)             as payment_terms_days,
    cast(branch_id as integer)                      as branch_id,
    cast(rep_id as integer)                         as rep_id,
    cast(discount_rate as {{ dbt.type_numeric() }}) as discount_rate,
    cast(credit_limit as {{ dbt.type_numeric() }})  as credit_limit,
    cast(created_at as date)                        as created_on,
    postal_code is null                             as is_missing_postal_code
from latest

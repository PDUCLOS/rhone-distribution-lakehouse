-- One row per invoice with its payment. Orphan invoices are excluded (quarantine).
with invoices as (
    select * from {{ ref('silver_invoices') }}
    where not is_orphan
),

payments as (
    select
        invoice_id,
        max(paid_on)        as paid_on,
        sum(amount_paid)    as amount_paid
    from {{ ref('silver_payments') }}
    group by invoice_id
),

orders as (
    select order_id, branch_id from {{ ref('silver_orders') }}
),

as_of as (
    select max(invoice_date) as as_of_date from invoices
)

select
    invoices.invoice_id                                         as facture_id,
    invoices.invoice_number                                     as numero_facture,
    -- Return-only orders produce negative invoices: credit notes
    case when invoices.amount_excl_tax < 0 then 'avoir' else 'facture' end as type_document,
    invoices.order_id                                           as commande_id,
    invoices.customer_id                                        as client_id,
    orders.branch_id                                            as agence_id,
    invoices.invoice_date                                       as date_facture,
    invoices.due_date                                           as date_echeance,
    invoices.amount_excl_tax                                    as montant_ht,
    invoices.vat_amount                                         as montant_tva,
    invoices.amount_excl_tax + invoices.vat_amount              as montant_ttc,
    payments.paid_on                                            as date_paiement,
    coalesce(payments.amount_paid, 0)                           as montant_paye,
    invoices.amount_excl_tax + invoices.vat_amount
        - coalesce(payments.amount_paid, 0)                     as reste_a_payer,
    invoices.status                                             as statut,
    {{ dbt.datediff('invoices.due_date',
                    'coalesce(payments.paid_on, as_of.as_of_date)', 'day') }} as jours_retard,
    coalesce(payments.paid_on, as_of.as_of_date) > invoices.due_date          as est_en_retard
from invoices
inner join orders
    on invoices.order_id = orders.order_id
left join payments
    on invoices.invoice_id = payments.invoice_id
cross join as_of

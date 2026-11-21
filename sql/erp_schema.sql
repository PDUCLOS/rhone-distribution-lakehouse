-- Operational source: the simulated ERP of Rhône Distribution (PostgreSQL).
-- Keys are declared but not every FK is enforced: real ERPs leak orphans, and
-- the injected anomalies (orphan invoices) must be loadable.
drop schema if exists erp cascade;
create schema erp;

create table erp.branches (
  branch_id int primary key, branch_code text not null, branch_name text not null,
  city text, postal_code text, opened_on date
);
create table erp.sales_reps (
  rep_id int primary key, branch_id int references erp.branches, first_name text, last_name text, hired_on date
);
create table erp.suppliers (
  supplier_id int primary key, supplier_name text not null, country_code text,
  standard_lead_time_days int, reliability_score numeric(4,3)
);
create table erp.products (
  product_id int primary key, sku text unique not null, product_name text, product_family text,
  sales_unit text, list_price_2024 numeric(12,2), unit_cost_2024 numeric(12,2),
  supplier_id int references erp.suppliers, is_active boolean
);
create table erp.customers (
  customer_id int primary key, account_code text unique not null, company_name text, segment text,
  naf_code text, size_band text, city text, postal_code text,
  contact_name text, contact_email text, contact_phone text, payment_terms_days int,
  branch_id int references erp.branches, rep_id int references erp.sales_reps,
  discount_rate numeric(5,3), credit_limit numeric(12,2), created_at date, updated_at timestamp
);
create table erp.sales_orders (
  order_id bigint primary key, customer_id int references erp.customers, branch_id int, rep_id int,
  channel text, order_date date, created_at timestamp, order_number text unique,
  status text, updated_at timestamp
);
create table erp.sales_order_lines (
  order_line_id bigint primary key, order_id bigint references erp.sales_orders, product_id int,
  qty_ordered int, qty_shipped int, unit_price numeric(12,2), unit_cost numeric(12,2),
  discount_rate numeric(5,3), is_return boolean, line_no int, created_at timestamp, updated_at timestamp
);
create table erp.shipments (
  shipment_id bigint primary key, order_id bigint, shipped_on date, delivered_on date, carrier text
);
create table erp.invoices (
  order_id bigint, customer_id int, invoice_id bigint primary key, invoice_number text unique,
  invoice_date date, due_date date, amount_excl_tax numeric(14,2), vat_amount numeric(14,2),
  status text, updated_at timestamp
);
create table erp.payments (
  payment_id bigint primary key, invoice_id bigint references erp.invoices, paid_on date,
  amount_paid numeric(14,2), payment_method text
);
create table erp.purchase_orders (
  purchase_order_id bigint primary key, supplier_id int, product_id int, ordered_on date,
  expected_on date, received_on date, qty_ordered int, unit_cost numeric(12,2)
);
create table erp.calendar (
  calendar_date date primary key, iso_day_of_week int, is_holiday boolean, is_business_day boolean
);

create index on erp.sales_orders (updated_at);
create index on erp.sales_order_lines (order_id);
create index on erp.invoices (updated_at);

-- =============================================================================
-- Rhône Distribution — Snowflake setup (slow path: nightly, aggregated)
-- Run once as SYSADMIN in a Snowsight worksheet. Idempotent.
-- Order: 01_setup.sql -> 02_security.sql -> push the extracts -> dbt build
-- =============================================================================
use role sysadmin;

-- Dedicated XS warehouse owned by SYSADMIN (so it can grant usage to the RD_* roles).
-- Suspends after 60 s idle to save credits.
create warehouse if not exists rd_wh
  warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true
  comment = 'Rhône Distribution: loads, dbt, Power BI';

create database if not exists rhone;
create schema if not exists rhone.bronze comment = 'Raw nightly extracts, append-only';
create schema if not exists rhone.silver comment = 'Typed, deduplicated, anomalies quarantined (dbt)';
create schema if not exists rhone.gold   comment = 'Star schema ready for Power BI (dbt)';
create schema if not exists rhone.security comment = 'Policies, tags and role-to-agency mapping';

use schema rhone.bronze;

create file format if not exists csv_gz
  type = csv
  compression = gzip
  parse_header = true
  field_optionally_enclosed_by = '"'
  null_if = ('')
  empty_field_as_null = true
  error_on_column_count_mismatch = false;

-- Internal stage: generator/push_to_snowflake.py uploads data/landing/snowflake/<batch>/ here
create stage if not exists landing file_format = csv_gz
  comment = 'Nightly ERP extracts, one folder per batch';

-- -----------------------------------------------------------------------------
-- Bronze tables (one per extract entity) + load lineage columns
-- -----------------------------------------------------------------------------
create table if not exists bronze.branches (
  branch_id NUMBER(38,0),
  branch_code VARCHAR,
  branch_name VARCHAR,
  city VARCHAR,
  postal_code VARCHAR,
  opened_on DATE,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.calendar (
  calendar_date DATE,
  iso_day_of_week NUMBER(38,0),
  is_holiday BOOLEAN,
  is_business_day BOOLEAN,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.customers (
  customer_id NUMBER(38,0),
  account_code VARCHAR,
  company_name VARCHAR,
  segment VARCHAR,
  naf_code VARCHAR,
  size_band VARCHAR,
  city VARCHAR,
  postal_code VARCHAR,
  contact_name VARCHAR,
  contact_email VARCHAR,
  contact_phone VARCHAR,
  payment_terms_days NUMBER(38,0),
  branch_id NUMBER(38,0),
  rep_id NUMBER(38,0),
  discount_rate NUMBER(14,3),
  credit_limit NUMBER(14,3),
  created_at DATE,
  updated_at TIMESTAMP_NTZ,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.daily_sales (
  sale_date DATE,
  customer_id NUMBER(38,0),
  product_id NUMBER(38,0),
  branch_id NUMBER(38,0),
  rep_id NUMBER(38,0),
  channel VARCHAR,
  order_count NUMBER(38,0),
  line_count NUMBER(38,0),
  qty_ordered NUMBER(38,0),
  qty_shipped NUMBER(38,0),
  qty_returned NUMBER(38,0),
  net_amount NUMBER(14,3),
  cost_amount NUMBER(14,3),
  ordered_amount NUMBER(14,3),
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.invoices (
  invoice_id NUMBER(38,0),
  invoice_number VARCHAR,
  order_id NUMBER(38,0),
  customer_id NUMBER(38,0),
  invoice_date DATE,
  due_date DATE,
  amount_excl_tax NUMBER(14,3),
  vat_amount NUMBER(14,3),
  status VARCHAR,
  updated_at TIMESTAMP_NTZ,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.orders (
  order_id NUMBER(38,0),
  order_number VARCHAR,
  customer_id NUMBER(38,0),
  branch_id NUMBER(38,0),
  rep_id NUMBER(38,0),
  channel VARCHAR,
  order_date DATE,
  status VARCHAR,
  created_at TIMESTAMP_NTZ,
  updated_at TIMESTAMP_NTZ,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.payments (
  payment_id NUMBER(38,0),
  invoice_id NUMBER(38,0),
  paid_on DATE,
  amount_paid NUMBER(14,3),
  payment_method VARCHAR,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.products (
  product_id NUMBER(38,0),
  sku VARCHAR,
  product_name VARCHAR,
  product_family VARCHAR,
  sales_unit VARCHAR,
  list_price_2024 NUMBER(14,3),
  unit_cost_2024 NUMBER(14,3),
  supplier_id NUMBER(38,0),
  is_active BOOLEAN,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.purchase_orders (
  purchase_order_id NUMBER(38,0),
  supplier_id NUMBER(38,0),
  product_id NUMBER(38,0),
  ordered_on DATE,
  expected_on DATE,
  received_on DATE,
  qty_ordered NUMBER(38,0),
  unit_cost NUMBER(14,3),
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.sales_reps (
  rep_id NUMBER(38,0),
  branch_id NUMBER(38,0),
  first_name VARCHAR,
  last_name VARCHAR,
  hired_on DATE,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.shipments (
  shipment_id NUMBER(38,0),
  order_id NUMBER(38,0),
  order_date DATE,
  shipped_on DATE,
  delivered_on DATE,
  carrier VARCHAR,
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

create table if not exists bronze.suppliers (
  supplier_id NUMBER(38,0),
  supplier_name VARCHAR,
  country_code VARCHAR,
  standard_lead_time_days NUMBER(38,0),
  reliability_score NUMBER(14,3),
  batch_id VARCHAR,
  extracted_at TIMESTAMP_NTZ,
  source_file VARCHAR,
  loaded_at TIMESTAMP_NTZ
);

-- -----------------------------------------------------------------------------
-- Load procedure: COPY every entity from every batch folder.
-- COPY keeps 64 days of load metadata, so already-loaded files are skipped:
-- re-running is safe (idempotent).
-- -----------------------------------------------------------------------------
create or replace procedure bronze.load_all()
returns varchar
language sql
as
$$
declare
  entities array default ['branches', 'calendar', 'customers', 'daily_sales', 'invoices', 'orders', 'payments', 'products', 'purchase_orders', 'sales_reps', 'shipments', 'suppliers'];
  loaded integer default 0;
begin
  for i in 0 to array_size(entities) - 1 do
    let entity varchar := entities[i]::varchar;
    execute immediate
      'copy into rhone.bronze.' || entity ||
      ' from @rhone.bronze.landing' ||
      ' pattern = ''.*/' || entity || '[.]csv[.]gz''' ||
      ' file_format = (format_name = rhone.bronze.csv_gz)' ||
      ' match_by_column_name = case_insensitive' ||
      ' include_metadata = (source_file = metadata$filename, loaded_at = metadata$start_scan_time)' ||
      ' on_error = abort_statement';
    loaded := loaded + 1;
  end for;
  return 'loaded ' || loaded || ' entities';
end;
$$;

-- Nightly at 06:00 Paris time, after the ERP extract (01:00) and the upload.
create or replace task bronze.nightly_load
  warehouse = rd_wh
  schedule = 'USING CRON 0 6 * * * Europe/Paris'
  comment = 'Load the nightly ERP extract into bronze'
as
  call rhone.bronze.load_all();

-- Tasks are created suspended. Resume when the pipeline runs daily:
-- alter task rhone.bronze.nightly_load resume;

-- First load (backfill) by hand:
-- call rhone.bronze.load_all();
-- select table_name, row_count from rhone.information_schema.tables where table_schema = 'BRONZE' order by 1;

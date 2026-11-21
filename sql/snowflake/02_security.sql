-- =============================================================================
-- Rhône Distribution — regulated access (simulated)
-- Roles, row access by agency, masking of personal data (GDPR) and of
-- commercially confidential figures, classification tags.
-- Run once as SECURITYADMIN / SYSADMIN, after 01_setup.sql. Idempotent.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Roles
-- -----------------------------------------------------------------------------
use role securityadmin;

create role if not exists rd_transformer           comment = 'dbt: builds silver and gold';
create role if not exists rd_daf                   comment = 'Finance: everything, unmasked';
create role if not exists rd_direction_commerciale comment = 'Sales direction: all agencies, margins visible, contacts masked';
create role if not exists rd_analyste              comment = 'Analysts: all agencies, personal data masked';
create role if not exists rd_powerbi_svc           comment = 'Power BI service account: gold read-only';
create role if not exists rd_commercial_lyg        comment = 'Sales rep, Lyon Gerland only';
create role if not exists rd_commercial_ven        comment = 'Sales rep, Vénissieux only';
create role if not exists rd_commercial_vil        comment = 'Sales rep, Villefranche only';
create role if not exists rd_commercial_bou        comment = 'Sales rep, Bourgoin-Jallieu only';
create role if not exists rd_commercial_ste        comment = 'Sales rep, Saint-Étienne only';

-- Keep every custom role under SYSADMIN (Snowflake best practice)
grant role rd_transformer           to role sysadmin;
grant role rd_daf                   to role sysadmin;
grant role rd_direction_commerciale to role sysadmin;
grant role rd_analyste              to role sysadmin;
grant role rd_powerbi_svc           to role sysadmin;
grant role rd_commercial_lyg        to role sysadmin;
grant role rd_commercial_ven        to role sysadmin;
grant role rd_commercial_vil        to role sysadmin;
grant role rd_commercial_bou        to role sysadmin;
grant role rd_commercial_ste        to role sysadmin;

-- Demo: let the current user switch into each role to show the policies at work
set me = current_user();
grant role rd_transformer           to user identifier($me);
grant role rd_daf                   to user identifier($me);
grant role rd_direction_commerciale to user identifier($me);
grant role rd_analyste              to user identifier($me);
grant role rd_powerbi_svc           to user identifier($me);
grant role rd_commercial_lyg        to user identifier($me);
grant role rd_commercial_ste        to user identifier($me);

-- -----------------------------------------------------------------------------
-- 2. Privileges
-- -----------------------------------------------------------------------------
use role sysadmin;

grant usage on warehouse rd_wh to role rd_transformer;
grant usage on database rhone to role rd_transformer;
grant usage on schema rhone.bronze to role rd_transformer;
grant select on all tables in schema rhone.bronze to role rd_transformer;
grant select on future tables in schema rhone.bronze to role rd_transformer;
grant all on schema rhone.silver to role rd_transformer;
grant all on schema rhone.gold to role rd_transformer;
grant usage on schema rhone.security to role rd_transformer;

-- Readers: gold only (bronze and silver are never exposed to business users)
create or replace procedure rhone.security.grant_gold_reader(role_name varchar)
returns varchar
language sql
as
$$
begin
  execute immediate 'grant usage on warehouse rd_wh to role ' || role_name;
  execute immediate 'grant usage on database rhone to role ' || role_name;
  execute immediate 'grant usage on schema rhone.gold to role ' || role_name;
  execute immediate 'grant select on all tables in schema rhone.gold to role ' || role_name;
  execute immediate 'grant select on future tables in schema rhone.gold to role ' || role_name;
  return 'gold reader: ' || role_name;
end;
$$;

call rhone.security.grant_gold_reader('rd_daf');
call rhone.security.grant_gold_reader('rd_direction_commerciale');
call rhone.security.grant_gold_reader('rd_analyste');
call rhone.security.grant_gold_reader('rd_powerbi_svc');
call rhone.security.grant_gold_reader('rd_commercial_lyg');
call rhone.security.grant_gold_reader('rd_commercial_ven');
call rhone.security.grant_gold_reader('rd_commercial_vil');
call rhone.security.grant_gold_reader('rd_commercial_bou');
call rhone.security.grant_gold_reader('rd_commercial_ste');

-- -----------------------------------------------------------------------------
-- 3. Role -> agency mapping (drives the row access policy)
-- -----------------------------------------------------------------------------
create table if not exists rhone.security.role_agence (
  role_name varchar not null,
  agence_id number not null
);
truncate table rhone.security.role_agence;
insert into rhone.security.role_agence values
  ('RD_COMMERCIAL_LYG', 1),
  ('RD_COMMERCIAL_VEN', 2),
  ('RD_COMMERCIAL_VIL', 3),
  ('RD_COMMERCIAL_BOU', 4),
  ('RD_COMMERCIAL_STE', 5);

-- -----------------------------------------------------------------------------
-- 4. Policies
-- -----------------------------------------------------------------------------

-- Policies test current_role(), not is_role_in_session(): with secondary roles
-- enabled (DEFAULT_SECONDARY_ROLES = ALL on recent accounts), a user holding
-- RD_DAF would otherwise see everything in clear under any role.

-- Agency filter: roles with a national scope see everything; a sales rep sees
-- only the rows of their agency. RD_TRANSFORMER must see everything, or dbt
-- incremental merges and tests would run on partial data.
create or replace row access policy rhone.security.agence_row_access
  as (p_agence_id number) returns boolean ->
    current_role() in ('RD_TRANSFORMER', 'RD_DAF', 'RD_DIRECTION_COMMERCIALE', 'RD_ANALYSTE', 'RD_POWERBI_SVC')
    or exists (
      select 1
      from rhone.security.role_agence m
      where m.role_name = current_role()
        and m.agence_id = p_agence_id   -- argument name differs from the column on purpose
    );

-- Personal data (contact name, e-mail, phone): finance and the agency sales
-- reps need them; analysts and the sales direction do not.
create or replace masking policy rhone.security.pii_masking
  as (val varchar) returns varchar ->
    case
      when current_role() in ('RD_TRANSFORMER', 'RD_DAF') then val
      when current_role() like 'RD_COMMERCIAL_%' then val
      when val like '%@%' then regexp_replace(val, '^[^@]+', '*****')
      else '*** masqué ***'
    end;

-- Purchase cost, gross margin, credit limit: commercially confidential.
create or replace masking policy rhone.security.finance_masking
  as (val number) returns number ->
    case
      when current_role() in ('RD_TRANSFORMER', 'RD_DAF', 'RD_DIRECTION_COMMERCIALE') then val
      else null
    end;

-- Classification tag, set by dbt from the column meta (pii / confidentiel_finance)
create tag if not exists rhone.security.classification
  allowed_values 'pii', 'confidentiel_finance'
  comment = 'Data classification, used by audits and access reviews';

-- dbt (RD_TRANSFORMER) attaches the policies and tags after each rebuild
grant apply on row access policy rhone.security.agence_row_access to role rd_transformer;
grant apply on masking policy rhone.security.pii_masking to role rd_transformer;
grant apply on masking policy rhone.security.finance_masking to role rd_transformer;
grant apply on tag rhone.security.classification to role rd_transformer;
grant select on table rhone.security.role_agence to role rd_transformer;

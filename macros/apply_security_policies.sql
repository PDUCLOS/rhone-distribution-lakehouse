{#-
  Snowflake only (no-op elsewhere). dbt recreates gold tables on each run, which
  drops attached policies, so they are re-attached in a post-hook. The policies
  themselves are created once by sql/snowflake/02_security.sql.
  Per-model rules come from meta in the YAML:
    meta:
      row_access: agence_id          # column filtered by agency
      masking:
        contact_email: pii_masking   # column -> policy name
  and column-level meta.classification (pii / confidentiel_finance) becomes a tag.
-#}
{% macro apply_security_policies() %}
    {%- if target.type != 'snowflake' -%}
        {{ return('select 1') }}
    {%- endif -%}
    {%- set meta = model.config.get('meta', {}) -%}
    {%- set statements = [] -%}
    {%- for column, policy in meta.get('masking', {}).items() -%}
        {%- do statements.append(
            'alter table ' ~ this ~ ' modify column ' ~ column ~
            ' set masking policy ' ~ target.database ~ '.security.' ~ policy ~ ' force') -%}
    {%- endfor -%}
    {%- for column_name, column in model.columns.items() -%}
        {%- if column.meta.get('classification') -%}
            {%- do statements.append(
                'alter table ' ~ this ~ ' modify column ' ~ column_name ~
                ' set tag ' ~ target.database ~ ".security.classification = '" ~ column.meta.get('classification') ~ "'") -%}
        {%- endif -%}
    {%- endfor -%}
    {%- if meta.get('row_access') -%}
        {#- Incremental tables keep their policy between runs: detach before re-attaching -#}
        {%- do statements.append('alter table ' ~ this ~ ' drop all row access policies') -%}
        {%- do statements.append(
            'alter table ' ~ this ~ ' add row access policy ' ~ target.database ~
            '.security.agence_row_access on (' ~ meta.get('row_access') ~ ')') -%}
    {%- endif -%}
    {#- One statement per call: the Snowflake connector rejects multi-statement strings by default -#}
    {%- if execute -%}
        {%- for statement in statements -%}
            {%- do run_query(statement) -%}
        {%- endfor -%}
    {%- endif -%}
    {{ return('select 1') }}
{% endmacro %}

{#-
  Bronze is append-only: a record extracted in several batches appears several
  times. Keep the most recent extraction of each key.
-#}
{% macro latest_version(source_relation, keys, order_by='extracted_at') -%}
    select *
    from (
        select
            src.*,
            row_number() over (
                partition by {{ keys | join(', ') }}
                order by {{ order_by }} desc
            ) as _version_rank
        from {{ source_relation }} as src
    ) as versions
    where _version_rank = 1
{%- endmacro %}

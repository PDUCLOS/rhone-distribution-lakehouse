{% test is_between(model, column_name, min_value=none, max_value=none) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and (
    {%- if min_value is not none %} {{ column_name }} < {{ min_value }} {%- endif %}
    {%- if min_value is not none and max_value is not none %} or {% endif %}
    {%- if max_value is not none %} {{ column_name }} > {{ max_value }} {%- endif %}
  )
{% endtest %}

{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

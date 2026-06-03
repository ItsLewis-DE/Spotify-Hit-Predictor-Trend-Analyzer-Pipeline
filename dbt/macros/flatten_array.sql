{% macro flatten_array(source_model, pk_columns, array_column, flattened_alias, cast_type='string') %}

{%- if pk_columns is string -%}
    {%- set pk_cols = pk_columns -%}
{%- else -%}
    {%- set pk_cols = pk_columns | join(', ') -%}
{%- endif -%}

SELECT 
    {{ pk_cols }},
    f.value::{{ cast_type }} AS {{ flattened_alias }}
FROM {{ ref(source_model) }},
LATERAL FLATTEN(input => {{ array_column }}) f

{% endmacro %}
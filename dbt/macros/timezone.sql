{% macro snowflake__current_timestamp() -%}
  convert_timezone('Asia/Ho_Chi_Minh', current_timestamp())
{%- endmacro %}

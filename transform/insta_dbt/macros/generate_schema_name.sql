-- 이 매크로는 dbt가 모델을 어떤 schema에 저장할지 최종 이름을 결정합니다.
-- 기본 dbt 동작은 target schema와 custom schema를 붙여서 STAGE_MART 같은 이름을 만들 수 있습니다.
-- 이 프로젝트는 stage는 정확히 STAGE, mart는 정확히 MART에 저장하는 것이 목적이므로
-- custom schema가 있으면 그 이름만 그대로 쓰고, 없으면 target schema만 사용하도록 고정합니다.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema | trim }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

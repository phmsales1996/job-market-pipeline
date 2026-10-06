
{% macro html_to_text(column_name) %}

{%- set entities = [
    ('&nbsp;', ' '), ('&zwj;', ''),
    ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&#39;', "'"), ('&apos;', "'"), ('&#43;', '+'),
    ('&rsquo;', "'"), ('&lsquo;', "'"), ('&ldquo;', '"'), ('&rdquo;', '"'), ('&acute;', "'"),
    ('&mdash;', '—'), ('&ndash;', '–'), ('&middot;', '·'), ('&bull;', '•'),
    ('&reg;', '®'), ('&trade;', '™'), ('&euro;', '€'), ('&pound;', '£'), ('&times;', '×'),
    ('&aacute;', 'á'), ('&agrave;', 'à'), ('&acirc;', 'â'), ('&atilde;', 'ã'),
    ('&eacute;', 'é'), ('&egrave;', 'è'), ('&ecirc;', 'ê'),
    ('&iacute;', 'í'), ('&iuml;', 'ï'),
    ('&oacute;', 'ó'), ('&ograve;', 'ò'), ('&ocirc;', 'ô'), ('&otilde;', 'õ'),
    ('&uacute;', 'ú'), ('&ugrave;', 'ù'), ('&ccedil;', 'ç'), ('&ntilde;', 'ñ'),
    ('&Aacute;', 'Á'), ('&Agrave;', 'À'), ('&Acirc;', 'Â'), ('&Atilde;', 'Ã'),
    ('&Eacute;', 'É'), ('&Ecirc;', 'Ê'), ('&Iacute;', 'Í'),
    ('&Oacute;', 'Ó'), ('&Ocirc;', 'Ô'), ('&Otilde;', 'Õ'), ('&Uacute;', 'Ú'), ('&Ccedil;', 'Ç'),
    ('&auml;', 'ä'), ('&ouml;', 'ö'), ('&uuml;', 'ü'), ('&Ouml;', 'Ö'), ('&szlig;', 'ß'),
] -%}

{#- Build nested replace(...) calls: each wraps the previous expression, innermost first. -#}
{%- set ns = namespace(expr="regexp_replace(" ~ column_name ~ ", r'<[^>]+>', ' ')") -%}
{%- for entity, character in entities -%}
    {%- set ns.expr = "replace(" ~ ns.expr ~ ", '" ~ entity ~ "', '" ~ character | replace("'", "\\'") ~ "')" -%}
{%- endfor -%}

trim(regexp_replace(replace({{ ns.expr }}, '&amp;', '&'), r'\s+', ' '))

{% endmacro %}

{#
    HTML fragment -> plain text, for sources without a reliable plain-text twin.
    Order matters: (1) strip tags, (2) decode the named entities below, (3) decode &amp;
    LAST so text escaped once is decoded once (&amp;nbsp; -> &nbsp;, not a space),
    (4) collapse whitespace, (5) trim.
    The entity list is driven by measurement (2026-10-04, all HTML sources): every entity
    seen in 2+ postings, plus the full set of Portuguese accented letters (the product's
    Brazil focus). HTML defines 2,000+ entities, so the list cannot be complete - leftovers
    are measured, not assumed. Tested by tests/assert_html_to_text.sql.
#}
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

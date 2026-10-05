-- Unit test for the html_to_text macro: known inputs, expected outputs.
-- Returns only the cases where the macro got it wrong (0 rows = pass). Each case guards
-- against one specific bug, named in its comment.
with cases as (

    select '<div><b>x</b></div>'         as input, 'x'           as expected union all  -- tags not removed
    select '<p>Hello</p><p>world</p>',            'Hello world'              union all  -- adjacent tags glue words
    select 'a&nbsp;b',                            'a b'                      union all  -- entity not decoded
    select 'I &lt;3 &quot;SQL&quot; &amp; it&#39;s fine', 'I <3 "SQL" & it\'s fine' union all  -- each entity
    select '&amp;nbsp;',                          '&nbsp;'                   union all  -- decoded twice (&amp; must run last)
    select '  a   b  ',                           'a b'                      union all  -- runs of spaces, edges
    select 'line one\n\n  line two',              'line one line two'        union all  -- newlines count as spaces
    select 'don&rsquo;t &mdash; really',          "don't — really"           union all  -- typographic entities
    select 'informa&ccedil;&atilde;o p&uacute;blica', 'informação pública'   union all  -- Portuguese letters
    select 'S&Atilde;O PAULO',                    'SÃO PAULO'                union all  -- uppercase too
    select 'a&zwj;b',                             'ab'                       union all  -- invisible joiner removed
    select cast(null as string),                  cast(null as string)                  -- NULL in, NULL out

)

select
    input,
    expected,
    {{ html_to_text('input') }} as actual
from cases
-- "is distinct from", not "!=": NULL != NULL is NULL (not true), which would hide a failure
where {{ html_to_text('input') }} is distinct from expected

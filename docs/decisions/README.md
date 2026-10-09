# Design decisions

Short records of the decisions that shaped this project: what was decided, the evidence it
was decided on, and what it cost. Each one was taken with real data in front of us, and most
of them replaced a first instinct that the data did not support.

They are written after the fact, from the working notes, and kept short on purpose.

| # | Decision | Area |
|---|---|---|
| [0001](0001-raw-layer-keeps-the-source-shape.md) | The raw layer keeps each source's shape and words | ingestion |
| [0002](0002-one-dag-per-source.md) | One DAG per source, on staggered schedules | orchestration |
| [0003](0003-canonical-key.md) | A posting is identified by source plus the source's id | modelling |
| [0004](0004-vocabularies-as-seeds.md) | Vocabularies are translated through seed tables | dbt |
| [0005](0005-html-to-text-in-dbt.md) | HTML becomes text in dbt, and leftovers are measured | dbt |
| [0006](0006-workplace-type-unknown-over-guessing.md) | Workplace type prefers "unknown" to a guess | modelling |
| [0007](0007-country-from-free-text.md) | Deriving a country from free text, and refusing two-letter codes | modelling |
| [0008](0008-fixed-menu-or-free-text.md) | A fixed menu gets a seed, free text gets a rule | modelling |
| [0009](0009-workable-descriptions-from-the-list.md) | Workable: descriptions from the list request | ingestion |
| [0010](0010-company-slug-stamped-by-the-loader.md) | The loader stamps the company on every posting | ingestion |
| [0011](0011-layers-and-the-union.md) | Translate per source, combine once | dbt |
| [0012](0012-star-schema-and-a-wide-mart.md) | A small star schema, and a wide table for using it | modelling |
| [0013](0013-warning-or-error.md) | When a test warns and when it fails | data quality |
| [0014](0014-open-or-closed.md) | Open or closed is worked out from absence, per source | modelling |
| [0015](0015-transform-when-ingestion-is-over.md) | The transform runs when ingestion is over, not at a time | orchestration |
| [0016](0016-dashboard-as-code.md) | The dashboard is code, built into a static page | serving |

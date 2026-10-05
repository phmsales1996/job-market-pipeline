# The dbt project (`job_market`)

Transforms the raw ATS tables (`dev_raw.*_postings`, loaded by the Python pipeline) into one
canonical shape. Layers: `staging` (one model per source: rename, translate, never drop rows) →
`intermediate` → `marts`. Built so far: `stg_lever_postings`, `stg_ashby_postings`, `stg_recruitee_postings`,
`stg_teamtailor_postings`.

The folder is called `dbt/` so the repo reads at a glance; the project itself is named
`job_market` in `dbt_project.yml`, which is also the name of the connection profile.

- **Seeds** (`seeds/`): mapping tables as data — workplace type and salary interval (keyed on
  source + raw value), country codes (generated from observed values by
  `scripts/generate_country_seed.py` against the ISO 3166 list).
- **Macro** `html_to_text`: HTML → plain text for sources without a reliable plain-text twin;
  unit-tested by `tests/assert_html_to_text.sql`.
- **Tests**: generic tests in `models/staging/_staging_models.yml`, singular tests in `tests/`
  (unmapped values, seed coverage, seed key uniqueness, no leftover HTML).

```bash
dbt build                      # seeds, models and tests, in dependency order
dbt source freshness           # are the raw tables still being loaded?
dbt docs generate && dbt docs serve --port 8081
```

Connection details live in `~/.dbt/profiles.yml` (profile `job_market`), never in this repo.

# Dashboard

**Live:** <https://phmsales1996.github.io/job-market-pipeline/>

A dashboard written as code with [Quarto](https://quarto.org/docs/dashboards/): one text file,
`index.qmd`, holding the queries (Python + SQL against the marts) and the charts. Quarto runs it
once and produces a plain web page, so nothing has to be running for someone to view it.

| Page | Shows |
|---|---|
| Overview | headline numbers; open remote postings by region, employment type, country and company; workplace type by source |
| Remote jobs | the most recent open remote postings, searchable, each linking to its posting |
| Companies | the companies with the most open remote postings |
| Pipeline | BigQuery data read per day, and each source's open and closed postings, last run and description coverage |

It reads only the marts (`remote_jobs`, `fct_job_postings`), never the raw tables.

```bash
pip install -r dashboard/requirements.txt  # once; Quarto itself is installed separately
quarto preview dashboard/index.qmd         # live preview while editing
quarto render dashboard/index.qmd          # build the page
```

Needs Google credentials that can read the marts, the same as the pipeline. The rendered files
are not committed (see `.gitignore`).

Every chart has a Table tab with the same data. `custom.scss` holds the look: one surface, one
font, thin single-colour marks, colour only where it distinguishes categories.

## Publishing

The built page is served by GitHub Pages from the `gh-pages` branch, which holds only the
rendered files (`index.html`, `index_files/`). For now it is published by hand after a render;
the plan is for the nightly transform run to rebuild and publish it.


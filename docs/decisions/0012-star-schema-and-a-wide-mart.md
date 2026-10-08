# 0012. A small star schema, and a wide table for using it

Status: accepted, October 2026. One dimension so far.

## Context
Two needs pull in different directions. The data has real dimensions: countries with names
and regions, companies that change over time, sources that differ in what they can express.
Someone looking for a job wants one flat table.

## Decision
Build both, the second on top of the first.
- **A star.** `fct_job_postings`, one row per posting, carries the posting's own attributes
  and the key of each dimension. `dim_country` is the first dimension.
- **A wide table named after its question.** `remote_jobs`: remote postings with the company
  name, country name and region already joined in.

The star is how the data is modelled; the wide table is how it is served.

## Details that were decided along the way
- **Two seeds for two questions.** One maps every spelling a source sends to a country code,
  with many rows per country. The other describes each country once. Putting names and
  regions on the first would repeat them on every spelling.
- **An "unknown" row.** About one posting in ten states no country. An empty value cannot be
  a join key, since an empty value never equals another, so those postings get a reserved
  code and the dimension has a row for it. Totals by region then add up to the number of
  postings, instead of quietly losing a tenth.
- **Standard regions, plus a visible rule.** The United Nations region and sub-region are kept
  as published. The business region (NAMER, LATAM, EMEA, APAC) is a grouping on top of them,
  in one place, with its judgement calls written down: Mexico follows the UN into Latin
  America, and Western Asia is the "ME" of EMEA.
- **A dimension is a model even when it starts as a copy of a seed.** Marts are the only
  layer promised to whoever queries, and the "unknown" row is logic an input file cannot hold.

## Consequences
- A region named in a job title is often the territory the job covers, not where its holder
  may live. Only the country's region is modelled so far.
- Still to build: a company dimension that keeps history, a daily snapshot fact, and the
  open-or-closed state of a posting.

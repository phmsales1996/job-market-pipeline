# 0016. The dashboard is code, built into a static page

Status: accepted, October 2026

## Context
Nothing consumed the marts. The postings themselves say which tools the market names: among
data roles, Power BI in 25%, Tableau in 24%, Looker in 16%, and no code-based dashboard tool at
all. So a dashboard written as code adds no keyword; it was chosen for other reasons.

## Decision
The dashboard is one text file of queries and charts (Quarto), kept in the repository, reading
only the marts. It is built into a static page and served from GitHub Pages.

## Why
- **It is reviewed and versioned like everything else.** A change to a chart is a diff.
- **A static page costs nothing to view.** The queries run once, at build time; a visitor needs
  no access to the warehouse and triggers no query.
- **It is public by default**, which suits a portfolio project built on public data.

## What was tried first
A tool chosen for exactly these properties turned out to have been rebuilt: it no longer exports
a static site, and self-hosting it means a running server with live queries. That was found only
when its starter project printed a deprecation notice. The lesson recorded here: check a tool's
current state by running it, before designing around what it used to do.

## Consequences
- No cross-filtering: a static page cannot re-query on a click. Search and sort on tables work
  in the browser.
- Defaults are not a design. The first page, one chart with every default on, looked poor; the
  same tool with one deliberate style did not. Single numbers are tiles, single measures use one
  colour, colour is reserved for categories, and every chart has a table of the same data.
- The page is a snapshot until something rebuilds it. Rebuilding and publishing it after the
  nightly transform is the next step.
- One page shows the pipeline's own numbers, including data read from the warehouse per day.

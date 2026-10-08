# 0010. The loader stamps the company on every posting

Status: accepted, October 2026

## Context
Sources are fetched one company board at a time, and most do not repeat the company inside
each posting. Only one source's payload carries a company name. For the other five, a loaded
row could not say which company it belonged to: about 98,000 of 132,000 postings.

The board's identifier was known all along. It was in the path of the landed file, and the
loader read that path without writing it down. The design notes listed the column as
required; it had never been implemented.

## Decision
The shared loader takes the identifier from the file path and stamps it on every row as
`company_slug`, in the same place it stamps the pipeline's timestamps. One change, in the one
module every source passes through.

## Why
- A value the pipeline knows and the source does not send belongs where every source is
  handled alike, not in six loaders.
- The column was added to the tables before the code that writes it. The load refuses a field
  the table does not have, so the other order would have failed the next run.

## Consequences
- Every posting seen after the change has its company, and every identifier matches the
  companies registry.
- The nightly merge only updates a posting when a newer file contains it. A posting that had
  already closed is never in a newer file, so it never received the new column. Those rows,
  about 20,000, were deleted from the raw tables rather than repaired, which made the column
  required everywhere.
- The raw tables therefore begin, in effect, with the postings open when the change shipped.

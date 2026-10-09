# 0014. Open or closed is worked out from absence, per source

Status: accepted, October 2026

## Context
The tables keep a posting after the company takes it down, which is what will let us measure
how long postings stay up. But no source sends a "closed" signal: a closed posting simply stops
being returned. Without a rule, a table of remote jobs lists jobs nobody can apply to.

## Decision
A posting is open when it was last seen on the same day as its own source's most recent run.

## Why each part
- **Its own source's run, not the calendar.** Each source runs at its own hour. A rule like
  "last seen today" marks every posting of a source closed between midnight and that source's
  run, and marks a whole source closed on a night its run fails. Comparing with the source's own
  latest run does neither: after a failed run its postings stay open.
- **By day, not by exact time.** "Last seen" is the moment each company's file was saved, and a
  run saves one file per company over several minutes. Matching the exact latest time kept only
  the last company's postings: 367 of 29,379 for one source.
- **Not from the source's own field.** One source has a field saying whether a posting is listed.
  Checked against postings known to be closed, it was true for every one: an unlisted posting is
  never returned, so the last answer held is always from when it was listed.

## Consequences
- The first night after the rule, about 3,300 of 123,000 postings were closed; remote postings
  were 30% of the table and 46% of what closed.
- A posting missed for one night by a partial failure is marked closed until it is seen again.
- When it closed, and how long it was open, follow from the same two timestamps and are not
  built yet.

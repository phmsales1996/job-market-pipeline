# 0013. When a test warns and when it fails

Status: accepted, October 2026

## Context
A failing test stops everything downstream. Some conditions are worth knowing about every day
without being a reason to stop.

## Decision
A test fails by default. It is set to warn only when both are true:
1. the condition is a known, understood exception, and
2. its normal count is written down, so a change in that count means something.

When the exception goes away, the test goes back to failing.

## Examples
- **Stray markup pasted by companies.** About 130 postings in one source carry literal markup
  that is also visible on the job page. The count is in the test's comment. A jump well above
  it would mean markup the conversion does not handle.
- **A country that has always been present.** One source has sent a country for every posting
  so far. That is an observation, not a promise, so its absence warns rather than fails.
- **The company identifier.** While postings that closed before the identifier existed were
  still in the tables, an empty identifier was a warning with a known count per source. After
  those rows were removed, the same test was made to fail: an empty identifier now means the
  stamping broke.

## Why
A warning that is yellow every day stops being read. It earns its place only while someone
knows what number to expect.

## Consequences
- Each warning carries a number that has to be kept in mind or, better, enforced with
  thresholds. That refinement is not done yet.

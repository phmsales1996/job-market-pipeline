# 0007. Deriving a country from free text, and refusing two-letter codes

Status: accepted, October 2026

## Context
The largest source sends no country, only a location typed by each company: `Remote - US`,
`Seoul, South Korea`, `San Francisco, CA`, `London`.

## Decision
Take the last piece of the location text and accept it as a country only when:
1. it is a country name the country seed knows, or
2. it is exactly `US` or `UK`, or
3. it is a US state code or name, in which case the country is the United States.

Any other two-letter piece is refused. A bare city gives no country.

## Why
The obvious rule, "look the last piece up in the country seed", is wrong in a way no test
sees. US state codes and ISO country codes are both two letters and they collide: `CA` is
California here and Canada in ISO, `MA` is Massachusetts and Morocco. The naive rule moved
about 1,250 Californian postings to Canada, and every result was a valid country code.

Counting the two-letter matches separately from the name matches is what made it visible.

## Consequences
- Coverage is 66% of that source's postings: 48% by name and the two trusted codes, the rest
  from US states.
- Known gaps: bare cities, and one name that is both a US state and a country.
- The column is documented as derived, with the rule, so nobody mistakes it for something
  the source said.

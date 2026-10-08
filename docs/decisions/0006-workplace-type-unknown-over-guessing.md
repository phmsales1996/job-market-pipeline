# 0006. Workplace type prefers "unknown" to a guess

Status: accepted, October 2026

## Context
"Is this job remote?" is the main question the project exists to answer, and no two sources
state it the same way. One has no field for it at all.

## Decision
One column, four values: `remote`, `hybrid`, `in_person`, `unknown`. A source's rule may be
generous about what it can read and must not invent what it cannot. Each rule was chosen
after looking at the data, and the source's own value is kept beside the result.

| Source states it as | Rule | Evidence |
|---|---|---|
| One word | translate through a seed | |
| One word, where 61% say `none` | `none` means in person | sampled postings were not remote; 0.3% of their titles mention remote or hybrid; the share matches another source's on-site share |
| Three independent booleans, 9% with more than one set | the most flexible option offered wins | the postings flagged remote and on-site, opened one by one, were remote roles. The opposite rule would have hidden 19% of the postings flagged remote |
| A word that arrives later, plus a flag that is always there | the word when present; else the flag only when it means remote; else `unknown` | where both exist: flag true was remote 152 times of 152; flag false was on-site 349 times and hybrid 149 |
| Nothing, only a free-text location | `remote` when the text mentions it; else `unknown` | "remote" appears in 24% of locations, in line with the other sources; "hybrid" in 2%, "on-site" in 0.2% |

## Why
- Defaulting a missing answer to `in_person` fabricates data, and for the largest source it
  would have fabricated it for every row.
- A text that is unreliable in one direction is still useful in the other: companies write
  "Remote" in a location box and almost never write "on-site".

## Consequences
- `remote` does not mean exactly the same thing in every source. For two of them it means
  remote is offered, possibly among other options. This is written in each column's
  description.
- A large share of postings is `unknown`. Reading the descriptions is the planned way to
  reduce it.

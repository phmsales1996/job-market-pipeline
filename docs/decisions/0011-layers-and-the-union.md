# 0011. Translate per source, combine once

Status: accepted, October 2026

## Context
With six staging models in place, the question was what belongs in each layer, and what
happens to columns that only some sources have.

## Decision
- **Staging** translates one source into shared names and values. It joins only to seeds, and
  it never drops a row.
- **Intermediate** combines. One model stacks the six staging models with `union all`.
  Anything shared by all sources and stored once elsewhere is joined here, once: the company
  name comes from the registry in a single join after the stack.
- A column goes into the union when at least two sources have it. A source that lacks it
  supplies a typed empty value so the stack stays aligned.
- A column only one source has stays in its staging model until a mart needs it.
- The union carries the translated columns. Each source's original wording stays in staging,
  where it is tested.

## Why
- Adding the company name in staging would have been the same join written six times.
- A column one source has would be empty for most of the union: width without an answer.

## What can go wrong, and the guard
A join can change the row count in both directions, and SQL considers both valid.
- An inner join to the registry dropped every posting without a company identifier.
- A join on the identifier alone would have doubled postings whose identifier exists on two
  job boards. The registry's key is the pair, source and identifier.
- A typed empty value written for a source that does have the column discards its data.

The guards: the union must have exactly as many rows as the six staging models together, the
key must be unique ([0003](0003-canonical-key.md)), and each column's fill per source is
compared with staging after a change.

## Consequences
- Six hand-written blocks of the same column list. A loop would remove the repetition; it is
  left until the list stops changing.

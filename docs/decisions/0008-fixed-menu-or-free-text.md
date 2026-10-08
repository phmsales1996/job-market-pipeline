# 0008. A fixed menu gets a seed, free text gets a rule

Status: accepted, October 2026

## Context
Employment type looked like one more vocabulary to translate. Three sources offer a fixed
menu of 5 to 14 values. The fourth lets each company type anything: about 200 different
values, mixing employment types with places, seniority and department names.

## Decision
- The three fixed menus go through a seed, like every other vocabulary
  ([0004](0004-vocabularies-as-seeds.md)).
- The free-text field is read by a pattern rule: the first match wins, ordered from specific
  to general (internship, temporary, contract, part time, full time).
- Text that names no employment type gives an empty value, not `other`.

## Why
- A seed needs a "must be mapped" test to be safe. On free text that test would fail every
  week, and a test that always fails gets ignored.
- The rule reads 95% of what companies typed. The four commonest spellings of "full time"
  are 78% of the field; the mess is in the tail.
- `other` means the source named a type that is not on our list. A value like "Sales" names
  no type at all, and saying so keeps the two apart.

## Consequences
- Order is part of the rule: "Contractor Full-Time" is a contract, "Intern / Part-Time" an
  internship. It is written in the column's description.
- One source's codes carry two facts, hours and contract length. Only the hours are kept in
  the canonical column; the original code stays beside it.

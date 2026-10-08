# 0005. HTML becomes text in dbt, and leftovers are measured

Status: accepted, October 2026

## Context
Four sources send job descriptions as HTML. The canonical model wants plain text. One source
offers plain-text twins of its fields, but they turned out to be empty for about half of its
postings, and one of its sections has no twin at all.

## Decision
- Conversion happens in dbt, in one macro, `html_to_text`: remove tags, turn a measured list
  of character codes into characters (the ampersand last), collapse whitespace.
- The macro is unit-tested on literal cases.
- What it leaves behind is counted by a test rather than assumed to be zero.

## Why
- One implementation for every source, versioned, tested and visible in the lineage.
  Converting in the Python loaders would have meant six loaders and six raw tables changing,
  with interpretation creeping into the raw layer.
- A regular expression is not an HTML parser. Measuring the leftovers is the honest answer
  to that weakness.

## Evidence that shaped it
- **Escaped HTML.** One source stores its tags as codes (`&lt;p&gt;`). One pass of the macro
  finds no tags, then turns the codes into real tags: it creates the markup it should remove.
  Applying the macro to its own output fixes it, with no change to the macro.
- **Faithful, not broken.** In one source about 130 postings still showed a literal `<p>`
  after conversion. Traced to raw, the company had pasted text from a word processor and the
  source stored the stray markup as escaped text; a visitor sees it on the job page too. The
  test for that source is a warning with a known count, not a failure.

## Consequences
- Sources that split their text into sections need an assembly rule, written per source and
  checked against the order on the real job page.
- The entity list is finite. A posting in a language with unlisted character codes would show
  them; the leftover count is where that would appear.

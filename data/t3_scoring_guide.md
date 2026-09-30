# Trade T3 scoring guide (Chris)

Ten generated papers (`data/t3_sample.json`, seed 635550), three parsers.
Parser outputs are in `data/cache/t3/<paper>/` (paper id with `/` and spaces
as `_`): `<parser>_refs.txt` (reference entries as delivered, numbered) and
`<parser>_tables.md` (every table found, in order, with caption or the line
before it). The PDF is `data/raw/scientisttwo/<paper id>.pdf`.

## 1. Count in the PDF (`data/t3_pdf_counts.csv`, once per paper)

- `references`: number of entries in the PDF's reference list.
- `Table 1`, `Table 2`: number of **data cells** in the PDF's Table 1 and 2
  (row x column of values, excluding header and row-label cells). Write the
  count; if a table is too large, score its first 5 rows and say so in `note`
  (then count the same rows for every parser).

## 2. Score each parser (`data/t3_scores.csv`)

- `references` -> `correct` = entries delivered as **their own entry** with
  authors, title and year intact. Two references merged into one entry, or
  one split across entries, count as wrong (for all pieces). Stray
  line-number digits or lost italics alone do not make an entry wrong.
- `Table N` -> `correct` = data cells whose value appears in the **right row
  and column** of the parser's version of that table. Find the table by its
  caption (GROBID, Docling) or its position (pymupdf4llm); if the parser
  missed the table entirely, `correct` = 0.

Score = correct / in_pdf, per parser, averaged over papers. Automatic
measures (seconds per paper, entries extracted, tables found) are in
`data/t3_auto.csv`; setup effort is recorded in docs/04.

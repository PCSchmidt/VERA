# Trade T3 scoring guide (lighter protocol)

Ten generated papers (`data/t3_sample.json`, seed 635550), three parsers:
pymupdf4llm, grobid, docling. Agreed 2026-09-30: score a fixed subset of
each paper first, and score in full only if the result is close (see
Escalation).

## Files

- PDF: `data/raw/scientisttwo/<paper id>.pdf`
- Parser outputs: `data/cache/t3/<paper>/` (paper id with `/` and spaces as
  `_`): `<parser>_refs.txt` (reference entries as the parser delivered them,
  numbered) and `<parser>_tables.md` (every table found, in order, with its
  caption or the line before it).
- Record counts in `data/t3_pdf_counts.csv` and scores in `data/t3_scores.csv`.

## 1. From the PDF (`t3_pdf_counts.csv`, once per paper)

- `references`: `in_pdf` = the number of references scored: **15**, or all of
  them if the paper has fewer. Put the paper's total reference count in
  `note` (e.g. `total 42`).
- `Table 1`, `Table 2`: `in_pdf` = the number of **data cells in the first 5
  data rows** of that table in the PDF (values only; header rows and
  row-label cells excluded). If the table has fewer than 5 data rows, count
  them all.

## 2. Per parser (`t3_scores.csv`)

- `references`: `correct` = how many of the **PDF's first 15 references**
  appear in `<parser>_refs.txt` as **their own entry**, with authors, title
  and year intact. The entry can be anywhere in the file. A reference merged
  into an entry with another reference, or split across entries, is not
  correct. Stray line-number digits or lost italics alone don't make it wrong.
- `Table N`: `correct` = how many of the counted cells (first 5 data rows)
  appear with the **right value in the right row and column** of the parser's
  version of that table. Find it by caption (grobid, docling) or position
  (pymupdf4llm). If the parser missed the table, `correct` = 0.

Score = sum of `correct` / sum of `in_pdf` over the ten papers, per parser
and item (references, tables).

## Escalation

If the two best parsers' reference scores are within **10 percentage
points**, score those two parsers' full reference lists (set `in_pdf` to the
total and re-score). Same rule for tables, using full tables.

## Who scores

Chris, or an assistant working **from the PDFs and the parser output files
only** (not from `data/t3_auto.csv`, docs/04 or other summaries), with Chris
spot-checking some papers. Say which in the notes; the trade decision
records it.

# data/ — data dictionary

`data/raw/` is git-ignored: corpus PDFs are evaluation data, stored locally and
never re-hosted. Everything else here is committed.

## Source

ScientistTwo gallery: <https://scientist-two.github.io/>.
**Corpus = every generated paper the site lists**, whether or not it beat the
human baseline. The site's own headline counts (86 papers beating SOTA, 107
problems) are recorded in `corpus_discovery.json`, not assumed.

## `corpus_discovery.json` (written by `scripts/discover_corpus.py`)

| Field | Meaning |
|---|---|
| `source_url` | page or data file the listing came from |
| `retrieved` | `YYYY-MM-DD` |
| `site_stated_count` | number of generated papers the site states, or `null` if it states none |
| `discovered_count` | number of generated papers the script found |
| `explanation` | required when the counts differ or `site_stated_count` is `null` |
| `crosscheck_url` | second listing compared against (the site repo's file tree), or `null` if skipped |
| `papers` | one object per paper: `gen_paper_id`, `domain`, `subdomain`, `method_name`, `file` (site-relative path), `pdf_url` |

The site publishes no data file; the listing is the `paperData` object in its
`index.html`. The script also seeds `corpus_inventory.csv` with one row per paper,
keeping rows that already exist.

## `provenance.jsonl` (FND-C-02; one JSON object per downloaded file)

`{"path": "data/raw/<...>", "url": "...", "retrieved": "YYYY-MM-DD", "sha256": "<hex>"}`

`path` is repo-relative with forward slashes. Generated papers go under
`data/raw/scientisttwo/`, parent papers under `data/raw/parents/`; both need
records. Checked by `tools/checks/check_provenance.py`.

**This file is the single source for download facts** (URL, date, hash). The
inventory doesn't repeat them; it links by `gen_pdf_url`. `check_inventory.py`
checks both directions: every inventory URL has a record, and every
generated-paper record belongs to an inventory row.

## `corpus_inventory.csv` (one row per generated paper)

Every cell is filled. Where a value can't be determined, write `unknown`.
For code URLs, `none` means *checked, and no public code exists*; `unknown`
means *not determined*. The difference drives the code-availability rate (R1).

| Column | Allowed values / meaning |
|---|---|
| `gen_paper_id` | `<domain key>/<PDF file stem>` from the site listing, e.g. `applications/Health_Cartan-DEC-MiAE` (may contain spaces) |
| `domain`, `subdomain`, `method_name` | as the site lists them |
| `gen_pdf_url` | URL the PDF was fetched from, or `unknown` if no PDF was found. **Links to `provenance.jsonl`**, which alone holds the hash and retrieval date. Filled by `scripts/fetch_corpus.py` |
| `gen_code_url` | URL, `none`, or `unknown` |
| `parent_title`, `parent_venue` | the human paper whose problem and baseline the generated paper uses |
| `parent_id_arxiv_or_doi` | arXiv id (`2401.01234`), DOI, or `openreview:<forum id>` when the paper has neither (e.g. ICML 2026 papers not on arXiv; PMLR issues no DOIs); identifies the **parent problem** |
| `parent_code_url` | URL, `none`, or `unknown` |
| `reported_gain_pct` | improvement over the parent baseline **as the generated paper reports it**, in percent; `unknown` if not stated as a single number |
| `compute_class` | `cpu`, `single_gpu`, `multi_gpu`, or `unknown`, from the **parent** paper's experimental setup; rows sharing a parent problem share the value |
| `candidate_for_p3` | `yes` or `no`; 2–3 rows (distinct parent problems) are `yes`, and only `cpu`/`single_gpu` problems qualify |
| `notes` | free text; may be empty |

Checked by `tools/checks/check_inventory.py`.

## Parent papers

ScientistTwo's paper ([arXiv 2609.19644](https://arxiv.org/abs/2609.19644),
Appendix A.1, Tables 12–14) lists the 107 accepted papers whose problems and
codebases were its inputs (38 NeurIPS 2025, 5 ICLR 2026, 64 ICML 2026
spotlights). It does not say which generated paper came from which input.

- `parent_candidates.csv` (`scripts/map_parents.py`): those 107 titles with
  venue and short citation, parsed from the appendix. A `#` line records the
  source and retrieval date.
- `parent_papers.csv` (`scripts/resolve_parents.py`): each candidate resolved
  to an arXiv id or `openreview:<forum id>`, with the venue OpenReview reports
  and the local PDF under `data/raw/parents/` (which has a provenance record).
- `data/cache/` (git-ignored) holds extracted text and ranked parent
  suggestions per generated paper; derived from the corpus, so never committed.

A generated paper's parent is set in the inventory only after its text is
read against the suggestion; the `notes` column says what the evidence was.

- `parent_arxiv_hints.csv`: arXiv ids the title search misses, each with its
  source (e.g. cited by id in a generated paper). A hint is used only if the
  arXiv title matches.
- `inventory_flags.json`: the review record behind the inventory: per row,
  confidence in the parent choice, reviewer flags (citation problems, missing
  parent PDFs, compute judgment calls) and P3 hints, plus counts of generated
  papers whose header falsely claims ICLR 2025 publication.

Rows were filled per domain (`data/inventory_task.md` holds the shared
instructions) and merged by `scripts/merge_inventory_rows.py`, which rejects
unknown parents, a parent claimed twice, id or venue mismatches, and values
outside this dictionary. Code URLs hidden behind link text are read from the
PDFs' link annotations (`scripts/pdf_links.py`).

## `inventory_spotcheck.csv`

Drawn by `check_inventory.py --sample 10` (seeded, recorded). Chris fills
`verdict` (`correct` / `incorrect`) and `note` by checking each sampled row
against its sources. The sample can't be redrawn once any verdict exists.

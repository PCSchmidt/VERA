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
| `gen_paper_id` | stable id from the site (slug or index) |
| `domain`, `subdomain`, `method_name` | as the site lists them |
| `gen_pdf_url` | URL the PDF was fetched from, or `unknown` if no PDF was found. **Links to `provenance.jsonl`**, which alone holds the hash and retrieval date |
| `gen_code_url` | URL, `none`, or `unknown` |
| `parent_title`, `parent_venue` | the human paper whose problem and baseline the generated paper uses |
| `parent_id_arxiv_or_doi` | arXiv id (`2401.01234`) or DOI; identifies the **parent problem** |
| `parent_code_url` | URL, `none`, or `unknown` |
| `reported_gain_pct` | improvement over the parent baseline **as the generated paper reports it**, in percent; `unknown` if not stated as a single number |
| `compute_class` | `cpu`, `single_gpu`, `multi_gpu`, or `unknown`, from the **parent** paper's experimental setup; rows sharing a parent problem share the value |
| `candidate_for_p3` | `yes` or `no`; 2–3 rows (distinct parent problems) are `yes`, and only `cpu`/`single_gpu` problems qualify |
| `notes` | free text; may be empty |

Checked by `tools/checks/check_inventory.py`.

## `inventory_spotcheck.csv`

Drawn by `check_inventory.py --sample 10` (seeded, recorded). Chris fills
`verdict` (`correct` / `incorrect`) and `note` by checking each sampled row
against its sources. The sample can't be redrawn once any verdict exists.

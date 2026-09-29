# Inventory task: fill corpus rows for one domain (VERA Increment 0)

Repo root: `C:\Dev\AIEngineeringProjects\VERA` (Git Bash paths: `/c/Dev/AIEngineeringProjects/VERA`).
You fill inventory rows for the generated papers assigned to you, working
**offline from local files only**. Do not edit any repo file, do not run git,
do not download anything. Write exactly one output file (see Output).

## Inputs (all local)

- `data/corpus_discovery.json`: `papers[]` with `gen_paper_id`, `domain`,
  `subdomain`, `method_name`, `file`.
- Generated-paper text: `data/cache/clean/<domain key>/<file stem>.txt`
  (page markers `=== page N ===`; ICLR line numbers removed). The files contain
  control characters: **always use `grep -a`** or Python; plain grep prints
  "Binary file matches" and hides the text. On Windows set
  `PYTHONIOENCODING=utf-8` when printing from Python.
- Ranked parent suggestions: `data/cache/parent_suggestions.json`, keyed by
  `gen_paper_id`: top 3 of the 107 candidates with `tier` (2 = parent title
  appears verbatim in the paper, 1 = parent's short name is in the method
  name, 0 = word overlap only) and `how`.
- The 107 candidate parents (ScientistTwo's input papers): `data/parent_candidates.csv`
  (skip the `#` first line). Resolved parents: `data/parent_papers.csv` with
  `paper_id` (arXiv id or `openreview:<forum>`, or `unknown`), `parent_venue`,
  `pdf_path`. Parent text: `data/cache/text/parents/<paper_id with non-alnum
  -> _>.txt` (e.g. `2512.02494.txt`, `openreview_aUXiqhLh0S.txt`).
- Data dictionary: `data/README.md` (section `corpus_inventory.csv`).
- Worked examples: the five `optimization/...` rows in `data/corpus_inventory.csv`.
  Match their style and level of evidence.

## Method per generated paper

1. **Parent.** Read the generated paper's abstract and introduction and find
   the human state-of-the-art method it says it improves on. Confirm which of
   the 107 candidates that is. The suggestions are hints, not answers: tier-0
   suggestions are often wrong, and some papers cite several candidates. The
   parent is the paper whose problem and baseline the generated paper adopts
   (its main comparison), not just any citation. Each candidate is the parent
   of at most one generated paper; if you think two of your papers share a
   parent, say so in `flags`.
   If the paper describes the parent's method but cites it wrongly or not at
   all, still choose the parent and record the citation problem in notes (see
   the ALOT-DRO example).
2. **parent_title / parent_venue / parent_id_arxiv_or_doi**: copy
   `parent_title` and `parent_venue` exactly from parent_candidates.csv; id from
   parent_papers.csv `paper_id` (`unknown` if unresolved).
3. **gen_code_url**: `none` (ScientistTwo publishes no generated code) unless
   the generated paper itself contains a real code URL, in which case use it.
4. **parent_code_url**: the parent's own code repository URL from the parent
   paper text (strip trailing punctuation). Not other projects' repos it cites.
   `unknown` if the parent paper has no link or its PDF is unavailable.
5. **reported_gain_pct**: a number (e.g. `12.4`) **only** if the generated
   paper states a single relative improvement over the parent baseline as a
   percentage. Otherwise `unknown`, and quote the actual claim in notes.
   Do not compute a percentage yourself.
6. **compute_class** (`cpu`, `single_gpu`, `multi_gpu`, `unknown`): from the
   **parent** paper's stated experimental hardware. If the parent states none,
   infer from the workload and from any hardware the generated paper reports,
   and write "Compute: inferred (...)" in notes. `unknown` only if there is
   genuinely nothing to go on. Multiple GPUs used for training -> `multi_gpu`.
7. **candidate_for_p3**: always `no` (chosen later across all domains). But if
   the parent problem is `cpu`/`single_gpu` **and** its experiments look like
   they finish in minutes to an hour, add it to `p3_hint`.
8. **notes**: one line, three parts, like the examples:
   `Parent: <evidence>. Gain: <claim quoted/condensed>. Compute: <evidence>.`
   Add `Parent code: ...` or citation problems when relevant. Plain ASCII
   where possible; no line breaks; no double quotes inside.

Be efficient: grep for the parent's short name, "baseline", "state-of-the-art",
"SOTA", github, GPU/CPU/hardware terms, rather than reading whole papers.
Do not fabricate: if you can't find something, use `unknown` and say why.

## Output

Write `data/cache/inventory_rows/<your batch name>.json` (create the folder if
needed) as a JSON list, one object per assigned paper:

```json
{
  "gen_paper_id": "...",
  "gen_code_url": "none",
  "parent_title": "...", "parent_venue": "...", "parent_id_arxiv_or_doi": "...",
  "parent_code_url": "...", "reported_gain_pct": "unknown",
  "compute_class": "...", "candidate_for_p3": "no",
  "notes": "Parent: ... Gain: ... Compute: ...",
  "confidence": "high | medium | low",
  "p3_hint": "",
  "flags": ""
}
```

`confidence` is about the parent choice: high = paper names the parent/its
method as the baseline and cites it; medium = clear from method/title but the
citation is missing or odd; low = a guess. `flags` holds anything the reviewer
must look at (shared parents, missing parent PDF, citation problems, doubts).

Then reply with a short summary: rows written, any low-confidence rows, flags,
and p3 hints. Your reply is read by the orchestrating agent, not a human.

# VERA: Evidence Notes

Companion to `VERA.md`. Labels: **Confirmed** (seen in code, settings, tests or history), **Ran it** (run in this session), **Per the docs** (project documents say so; not checked), **My reading**, **Ask the author**, **Author says**. Paths here are repository-relative; the clone was `explainer-runs/VERA` at commit `a0015b0` (2026-10-19), read-only. The run scratch copy was a fresh `git clone` of that clone in the session scratch folder.

## E1 Fact sheet

| Fact | Value | Label |
| --- | --- | --- |
| Name, address, licence | VERA (Verifiable, Economical Research Agents); github.com/PCSchmidt/VERA; public; MIT; bundled DejaVu fonts under their own licence | Confirmed (`LICENSE`, `pyproject.toml`, `gh repo view`) |
| What it is | Local FastAPI app plus command-line scripts: topic, confirmed question, quoted literature review, optional review paper, per-sentence audit with a colour; a command-line research loop with a Docker sandbox | Confirmed (`vera/app/pipeline.py`, `vera/literature/graph.py`, `vera/loop/`) |
| Status | v1.0 closed 2026-10-15; showcase additions 2026-10-16; one docs commit 2026-10-19 | Per the docs (README, `docs/reviews/retrospective.md`); dates Confirmed from git |
| Size | `vera/` 13,884 lines of Python; `tests/` 10,911 lines; 1,687 tracked files | Ran it (`git ls-files` + `wc`) |
| Commits | 241, all under the author name Chris Schmidt; first 2026-09-29, last 2026-10-19; 217 carry a Claude trailer (Sonnet 5.5 x140, Opus 5.5 x77), 24 none | Ran it (`git log`) |
| Tests | 855 collected; scratch run without `tests/test_sandbox.py`: 828 passed, 4 skipped, 179 s; pilot run with Docker running (v1.1 map, M3): 851 passed, 4 skipped | Ran it / pilot (not repeated) |
| Lint | `ruff check .` clean | Ran it |
| CI | `meridian.yml` runs `scripts/meridian-verify.sh` (gate structure); `pages.yml` builds the showcase; both green on the last runs | Confirmed; `gh run list` |
| Deployed | Static showcase only (HTTP 200); the app is local by design (docs/04 T8) | Ran it (curl); Per the docs |
| Users | 0 stars, 0 forks, no issues or PRs; traffic API: 0 views, 169 clones (72 unique) in the last 14 days, source unknown | Ran it (`gh api`) |
| Needs | Python 3.11+, uv, an OpenRouter key for the app; optional Jev, OpenAlex, Semantic Scholar keys; optional GROBID in Docker; Docker plus datasets for the loop | Per the docs; Confirmed in `.env.example` names |
| Spend | $16.05 to the close, $1.88 after, inside a $20 monthly ceiling | Per the docs; script and ledgers mostly git-ignored, not reproducible from the clone |

Names of environment variables read: `OPENROUTER_API_KEY`, `TYPESAFE_AI_API_KEY`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `VERA_GENERATOR_MODEL`, `VERA_REQUIRE_DOCKER`. No `.env` was opened.

## E2 Reading and running log

Read: the questionnaire (v3.2), author context, README, CLAUDE.md, `docs/01-conops.md`, retrospective, increment reviews 1, 4, 7, 8, 9 (headline sections) and parts of 5 and 6, `docs/07-increments.md` (not-planned table), `docs/04-trade-studies.md` T1, T9, T11 and part of T8, `docs/meridian-dogfood.md` (top), `vera/judge/__init__.py`, `router.py`, `cheap_path.py`, `vera/literature/sentence_checks.py`, `vera/ledger/__init__.py`, `vera/backends/openrouter.py`, `generator.py`, `typesafe.py` (header), `vera/bench/candidates.py`, `vera/app/server.py` (top), `keystore.py`, `pipeline.py` (constants and `real_deps`), `vera/schemas/foundation.py` and `judge.py` (excerpts), workflows, `.meridian/gate-state.json`, `dogfood.jsonl`, `evaluator/*verdict*.json` (scores), result files `judge8_test.json`, `realcase_incr7_test.json`, `seeded_v3/results_test.json`, `spend_total.json`, `rubric_provenance.md`, a showcase example's claims and audit.

Reused as evidence after re-checking (prose discarded): the pilot map `v1.1/VERA.map.md` (fact sheet, gate table, claims list, discrepancy list). Items re-verified here: commit counts and trailers, test count, gates and approvals, evaluator scores, dogfood hours and escapes, judge8 and realcase numbers, seeded result, model constants, CI content, security settings. Items taken from the pilot and not re-run: the 851/4 full run with Docker, the three freeze-manifest hash recomputations, `check_app --part secrets` was re-run (OK), the loop internals.

Not read: any earlier VERA explainer (`VERA_MASTER_EXPLAINER.md` in the repo was not opened), `VERA.math.md`, any `.env`, `docs/05`, `docs/06`, most of `docs/02`/`03`, most of `vera/audit/` and `vera/loop/`, `data/` run folders other than the samples named.

Run in the scratch copy (not the clone): `uv sync --group dev --group bench --group corpus` (exit 0); `uv run pytest -q -p no:cacheprovider --ignore=tests/test_sandbox.py` (828 passed, 4 skipped, 2:59); `uv run ruff check .` (clean); `uv run pytest --co -q` (855); `check_app.py --part secrets` OK; `check_traceability.py` OK (36 requirements); `check_carry7.py --part measured` OK; `check_carry8.py --part measured` OK (no backend meets both bars); `check_carry5.py` BLOCK (ledger `data/ledger/run_retest5-1.jsonl` not in a clean clone); `check_seeded_v3.py` BLOCK ("the audit's source changed after it was frozen"). Docker was deliberately not used: `tests/test_sandbox.py` was excluded. `tests/test_app_ui.py` can launch a local headless browser if one is found; it is local and was left in. No model API was called; no network use by the tests was traced beyond the absence of keys. Scripts that overwrite tracked files (`reread9.py`, `reread10.py`, `spend_total.py`) were not run. Final `git status --short` in the clone: empty (`.venv` and caches are git-ignored).

## E3 Claims check

Levels: L1 doc matches a committed result file; L2 re-run; L3 recomputed.

| ID | Claim (source) | Check | Verdict |
| --- | --- | --- | --- |
| CL-01 | 855 tests (README) | L2: 855 collected | Supported |
| CL-02 | 50 of 52 planted faults caught; 3 of 6 controls failed (README) | L1 `seeded_v3/results_test.json` (red 50/52, false_fails 3 of 6); L2 `check_seeded_v3` BLOCKS at HEAD | Partly: result is for an earlier audit version |
| CL-03 | 15 of 21 faulty flagged; 14 of 69 sound flagged on 90 real items (README) | L1 and L2 (`check_carry7`); L3 sums from the JSON: claims 4/5, sentences 11/14, inference 0/2; sound 7/35, 4/12, 3/22 | Supported (labels are an AI assistant's) |
| CL-04 | Cheap judge agrees 89/95/89 percent on 162 items; bar 97 not met (README) | L1 `judge8_test.json`: 64/72, 41/43, 42/47; 72+43+47=162; L2 `check_carry8` OK | Supported |
| CL-05 | Jev alone 79/93/77; GLM alone 86/93/87 (README) | L1: 57/72, 40/43, 36/47; 62/72, 40/43, 41/47 | Supported |
| CL-06 | Jev calibration error 0.008 on the first benchmark; local model said 1.0 on 1,149 of 1,150 (README) | L1 against docs/04 T1 table (ECE 0.008, 0.006 GLM); the 1,149 figure is the docs' | Per the docs |
| CL-07 | Jev $0.042 per million input tokens (README) | Constant `4.2e-8` in `vera/bench/candidates.py`; vendor price not checked | Partly |
| CL-08 | A review costs $0.11 to $0.21, a paper $0.53 to $0.77 (README) | One run re-added from its committed ledger: 219 calls, $0.1849 (matches `showcase.json`); others not re-added | Partly (ledger figure is OpenRouter's reported cost, no invoice) |
| CL-09 | $16.05 total spend (README) | `spend_total.json` says 16.0522; ledgers mostly absent from a clone | Per the docs; not reproducible |
| CL-10 | Retrieval finds 59 percent of key papers (README) | docs state 34 of 58 (incr-4 review); not recomputed | Per the docs |
| CL-11 | Key held in memory only; foreign hosts and origins refused (README) | Code read; probe E4 | Supported |
| CL-12 | Every measured set frozen before its one test run, with one break (README) | `check_carry7/8` OK; `check_seeded_v3` blocks | Partly |
| CL-13 | Evaluator verdicts kept unedited (README) | 46 files present; scores read; unedited not verifiable beyond git | Partly |
| CL-14 | Human gates approved in Chris's terminal, two by an assistant (README) | `gate-state.json`: 43 approvals all "Chris Schmidt"; incr-7 review names the assistant | Supported, record mismatch noted |
| CL-15 | GitHub description: an integrity auditor of papers' citations, claims, code and novelty | `gh api` description text; external-paper auditing not built (docs/07 not-planned) | Contradicted for outside papers |
| CL-16 | Blind rubric means 4.27 vs 2.93 (reviews), 3.94 vs 3.17 (papers) | Read in incr-5 and incr-6 text; JSON scores not recomputed | Per the docs |
| CL-17 | "Cheap judge answers every check first"; "Jev answers first" (README) | `cheap_path.py`: `lit.*` and `loop.*` skip Jev | Contradicted in part (disclosed elsewhere) |
| CL-18 | The five-increment history | Commits per day counted | Supported |

## E4 Rule attacks

Probe scripts were written outside the clone and run in the scratch copy; outputs below.

| Probe | Result |
| --- | --- |
| `Budget.charge(0.20)` on a $0.10 cap | `BudgetExceeded`; `spent_usd` stays 0.0 |
| `metered_call` with an estimate over the cap | `BudgetExceeded`; call not made; ledger empty |
| `metered_call` whose call raises | Record written with `RuntimeError: boom`, cost 0.0; budget calls 1, spent 0.0 |
| `parse_answer` on "", prose, a non-boolean answer, no probability, probability 7 | Confidence 0.0, source `none` in each; valid answer with probability 0.9 gives 0.9 `self_report` |
| `Verdict` with `judge_id == producer_id` | Pydantic `ValidationError` wrapping `SelfGradingError` |
| `quote_in_text`: exact, one word inserted, 20-character quote, case and spacing change | True, False, False, True |
| `agreement_problem`: "agree" with premises from one source / two sources / no agreement word | Flagged / None / None |
| `absence_problem` | "No study examines long-run drift" and "The evidence does not cover small samples" caught; "No evidence of harm was found in the trial" not caught |
| `names_a_source` | "Smith and colleagues" caught; "Barber et al." caught ("et al"); "The Gibbs group studied it." missed; "Work by the Gibbs group" caught (the pattern needs a lowercase "the") |
| `leans_on_context` | "However, this patch..." True; plain statement False |
| Server with `Host: evil.example.com` | 403 |
| Cross-origin POST of a key (`Origin: http://evil.example.com`) | 403; key not set |
| Key of 5 characters; unknown field in the key body | 400; 422 |
| Config response after a key is set | Does not contain the key text |

Not probed: the sandbox (needs Docker), the stop file, resume after a crash, PDF generation.

## E5 Code map

`vera/schemas` (data contracts, schema version 0.13 per docs/03); `vera/ledger` (append-only call record, `metered_call`); `vera/backends` (the only vendor HTTP: OpenRouter judge and generator, TypeSafe, Ollama; key lookup and redaction); `vera/judge` (prompt and parse, router, cheap path); `vera/graph` (LangGraph helpers, checkpoints); `vera/literature` (scoping, retrieval, reading, synthesis, sentence checks, paper stage); `vera/audit` (citations, numbers, figures, sentences, disagreement, sticky answers, seeded sets); `vera/loop` (research loop, command line); `vera/sandbox` (Docker runner); `vera/app` (server, run manager, worker, key store, PDF, static front end); `vera/bench` (benchmark and the production model registry `candidates.py`). Entry points: `vera-app` (`vera.app.server:main`), `python -m vera.app.worker`, scripts under `scripts/`.

## E6 Model call sites

| Role | Model (OpenRouter id) | Settings | Site |
| --- | --- | --- | --- |
| Writer, scoping, queries, repair, paper | `anthropic/claude-sonnet-5.5` (or `VERA_GENERATOR_MODEL`) | temperature 0.7, reasoning effort minimal, 8,000 max tokens | `vera/app/pipeline.py`, `vera/backends/generator.py` |
| Cheap judge, first | Jev `jev-latest` through `api.typesafe.ai/v1/systemone`, all questions in one call | probability per answer; price constant $4.2e-8 per input token | `vera/backends/typesafe.py` |
| Cheap judge, second | `z-ai/glm-5.3-flash` | temperature 0, JSON mode, logprobs when offered, 2,048 tokens (6,000 on the loop/literature path), reasoning minimal on that path | `vera/judge/cheap_path.py`, `vera/backends/openrouter.py` |
| Reference judge | `anthropic/claude-sonnet-5.5` | temperature 0, 2,048 tokens | `cheap_path.confirmer`, `QUESTION_ROUTES`, `CONFIRM_NO` |
| Benchmark only | `xiaomi/mimo-v2.6-flash`, `deepseek/deepseek-v4.1-flash`, local `gemma4:12b` (Ollama) | see `vera/bench/candidates.py` | `vera/bench/` |
| Loop arms | `xiaomi/mimo-v2.6-pro` and the above | per docs/04 T9 | `scripts/run_loop.py` |

Routing: `QUESTION_ROUTES` sends `claim.within_quote`, `sentence.no_fact`, `paper.inference_follows` to Jev then GLM; all `loop.*` and `lit.*` question ids go to GLM only (`CheapPath.router_for`); with no Jev key GLM answers every question. `CONFIRM_NO` re-asks the reference on a cheap no for `claim.within_quote` and `paper.inference_follows`. Threshold 0.7 (`RoutingPolicy`, `MIN_CONFIDENCE` in `vera/audit/disagreement.py`). GROBID (`lfoppiano/grobid:0.8.2`) is a separate local service.

Cost evidence: `data/app/live/rlm-vs-clm-2/ledger.jsonl`, 219 records, $0.1849; `anthropic/claude-sonnet-5.5` 5 calls $0.1744; `z-ai/glm-5.3-flash` 214 calls $0.0105; components `p2.cheap_path` 214, `p3.synthesize` 2, `p3.scope`, `p3.retrieve`, `p3.parent` 1 each (Confirmed). No Jev calls in that run.

## E7 Tests and CI

855 tests in 76 test files plus helpers, all with fake model backends (`tests/lit_fakes.py`, `tests/loop_fakes.py`). Scratch result and commands in E2. Three spot-checked tests: `tests/test_ledger.py::test_FND_F_01_call_over_budget_raises_before_it_is_made` (asserts the call list is empty, ledger empty, budget unchanged: real behaviour); `test_FND_F_01_failed_call_is_recorded_and_reraised` (asserts error text, zero cost, one call counted); `tests/test_sentence_checks.py` cases built from the defects Increment 6's green audits missed (regression guard written after the fact). Coverage was not measured in this session. CI: `meridian.yml` runs only `scripts/meridian-verify.sh` (gate DAG and state; no pytest, no ruff, no content scan, per `scripts/meridian-verify.sh`); `pages.yml` builds the static site on listed paths. The dogfood log itself records the missing content scan as an escape (2026-10-01). Sandbox tests (23 in `test_sandbox.py`) skip without Docker unless `VERA_REQUIRE_DOCKER=1`.

## E8 Plan versus results, and history

Freeze records: `data/results/audit_hash_incr5.json`, `inference_hash_incr6.json`, `realcase_hash_incr7.json`, `judge8_hash.json`; measured-after-freeze checks pass for realcase (freeze then run at 2026-10-13T16:52:39Z) and judge8 (2026-10-14T12:57:05Z) (Ran it). These timestamps are written by the project's own scripts; no outside push-time record was consulted (GitHub events reach back about 90 days; the repository is 4 weeks old, but push times were not pulled). The audit freeze was broken once (Increment 4 review; `vera/loop/tables.py` changed at 2026-10-04T21:21Z); `check_seeded_v3` blocks at HEAD (Ran it). Commit dates: 12, 33, 17, 34, 19, 64, 7, 1, 21, 18, 2, 2, 8, 2, 1 commits per day from 09-29 to 10-19 (Ran it). Bulk commits: `4cee902` (136 files, +15,593), `9d7e721` (122 files, +38,770), `e672ba7` (63, +14,980), `a636eec` (79, +30,132) (Ran it). Credits by tool: Claude Sonnet 5.5 140, Claude Opus 5.5 77 (one "1M context"), none 24.

## E9 Gates and approvals

`.meridian/gates.yaml` 89 gates (43 human, 46 automated per the pilot count); `gate-state.json`: 89 passed, 43 approvals, every `by` is "Chris Schmidt" (Ran it). The incr-7 review (and README) say an OpenAI assistant approved `realcase_labelled` and `paper_rerun` in Chris's name; the state file cannot show that. The gate `newuser_walkthrough` (label asks for a person other than the builder) passed with the builder (`independent_of_builder: false`, incr-5 review). Evaluator verdict scores (final / first round): incr0 8 pass; incr1 8.3 pass (first 8.1); incr2 8.0 (7.4); incr3 7.3 (first fail 6.2); incr4 8.3 (first fail 6.2); incr5 7.8 (first fail 6.0); incr6 8.0 (first warn 7.0); incr7 8.3 (warn 7.2); incr8 8.5 (warn 7.3); incr9 8.4 (first fail 5.5); incr10 8.4 (warn 6.8). Dogfood log: 12 overhead entries summing 34.0 hours, 4 escapes (2026-10-01 high, 2026-10-03 medium x2, 2026-10-03 low). The retrospective says 32 hours (29.5 after a correction); the log has one later 2-hour entry (My reading: explains the difference).

## E10 Environment

Python 3.12 was chosen by uv (`requires-python >= 3.11`); `uv.lock` is committed; plain `uv sync` strips the optional groups the tests need (CLAUDE.md note); the README quickstart uses plain `uv sync` for the app. The result files record model ids and ledgers; package versions are not recorded in results. Fresh install worked in the scratch copy with the three groups.

## E11 Security and privacy

Pattern scan of the full git history (`git log --all -p`) for OpenRouter, Anthropic, GitHub and AWS key shapes: 0 matches (Ran it). `check_app.py --part secrets` OK (no key-shaped string in tracked files, `.env` untracked, leak, argv and origin tests present, no external page loads, CSP set). GitHub settings (`gh api`): secret scanning enabled, push protection enabled, Dependabot security updates disabled, branch protection absent on `main` (404), no issues or PRs. The app listens on 127.0.0.1 only; the key lives in `SessionKey` and the worker's environment. Outside services: OpenRouter, TypeSafe (optional), arXiv, Crossref, OpenAlex, Semantic Scholar, GitHub API, doi.org. Third-party PDFs are git-ignored. The TypeSafe terms forbid using Jev output to train a model (per `docs/04` T1).

## E12 Shortcomings register (main items)

| ID | Shortcoming | Severity | Disclosed? | Options and recommendation |
| --- | --- | --- | --- | --- |
| S1 | The yardstick for the judges is a model (the reference, which is also the writer); labels for real-text tests came from an AI assistant; reference unsure on about a fifth and agrees with the assistant's labels 69 percent (claims) | High | Yes (README limitations) | A: a person labels a sample (medium effort, high payoff); B: a vote of several strong models (small, medium); C: leave and document. Recommend A |
| S2 | Stricter checks not shown to improve papers; one run per paper | Medium | Yes | Multi-run measurement (large) or leave closed |
| S3 | The 50 of 52 result belongs to an earlier audit; 3 of 6 controls failed | Medium | Partly (freeze break disclosed in incr-4) | Re-run the planted-fault test on current code (small cost, medium effort) |
| S4 | CI does not run tests or lint; the framework text calls CI the enforcement boundary | Medium | Dogfood escape logged | Add pytest and ruff to the workflow (small, high payoff) |
| S5 | No independent user (MOE-4) | Medium | Yes | One outside walkthrough (small) |
| S6 | Process records: two approvals recorded under the owner's name were run by an assistant; one gate label unmet but passed | Medium | Yes in reviews, not in state | Correct the state file or add an attribution field (small) |
| S7 | Documentation overstates: GitHub description; "answers every check first"; verify path that fails or overwrites tracked files | Low to medium | Partly | Edit text; write-protect the re-read scripts (small) |
| S8 | English wording rules have holes (capitalised "The X group", "No evidence of harm...") | Low | No | Case-insensitive match and more patterns (small) |
| S9 | Retrieval misses about 40 percent of key papers | Medium | Yes | Wider sources and queries (medium); not planned |
| S10 | Writer and reference judge are one model; the guard compares component names | Medium | Yes | A different-family reference (medium cost) |
| S11 | Self-reported costs, not invoices; spend total not reproducible | Low | Yes | Commit the ledgers or a summary |
| S12 | Two wordings under one question id (`paper.inference_follows`), prompt-text parsing in `audit/sticky.py` | Low | Docstring | Rename ids (small, but breaks freeze hashes) |

## E13 Math and method detail

Escalation: for question q, escalate if `confidence < threshold_for(q)`, default 0.7, at most one escalation. Verdict confidence: probability of the chosen answer; Jev boolean: p = P(yes), confidence max(p, 1-p) (`typesafe.py`). ECE: bins of stated confidence, mean absolute gap between mean confidence and accuracy, weighted by bin size (`vera/bench/metrics.py`, not re-read in detail). Confidence ranges: Wilson score interval, z = 1.96, from the repository's measurement scripts; the pooled range for 15 of 21 (0.50 to 0.86) and the 14 of 69 range (0.125 to 0.312) were computed here (L3). Budget: `charge` raises if any of dollars, seconds or calls would exceed its limit and leaves the budget unchanged; `metered_call` charges the worst-case estimate to a copy before the call and the actual cost after. Quote check: normalised substring test with a 25-character minimum (`reading.quote_in_text`).

## E14 Discrepancies

1. README calls the cheap judge the first answerer for every check; `lit.*` and `loop.*` skip Jev (`cheap_path.py`). 2. Framework text calls CI the enforcement boundary; CI checks gate structure only. 3. GitHub description versus built scope. 4. Gate state versus the incr-7 review on approver identity. 5. `newuser_walkthrough` gate label versus the record. 6. README says the reviewer path "842 passed, 13 skipped"; the current suite is 855 (dated snapshots, benign). 7. `check_carry5.py` blocks from a clean clone though listed as a verification step. 8. Retrospective 32 hours versus log 34.0. 9. README "ScientistTwo about $3,800 per task" versus "per-run cost is not published" (README line 293); source not found.

## E15 Production readiness detail

| Trait | Rating | Evidence |
| --- | --- | --- |
| Someone else can run it from a clean start | Partly | Install works; plain `uv sync` strips test dependencies; some verify commands fail |
| Automatic checks block a bad change | No | CI runs gate structure only |
| Quality measured against a baseline | Yes | Planted faults, real items, agreement sets; small and model-labelled |
| Behaves safely when things go wrong | Yes | Budget cap before calls, ledger, resume, fail-closed gates, sandbox with no network |
| People can review or stop the AI | Partly | Question confirmation and Stop; no review of output |
| Prompts, models and settings versioned | Partly | Git and freeze hashes; no prompt versions |
| Logs good enough to diagnose | Partly | Ledger and run files; no monitoring |
| Data and secrets handled safely | Yes | Key in memory only; scans clean; local server |

Placement: works locally. Gap to deployable: hosting (conflicts with the local-only decision T8), sign-in, monitoring and alerts, rollback, pinned model versions, security review, runbook, CI that runs the tests (all missing or partly there).

## E16 Review dispositions

No separate review pass had been run at the time of writing; the plain-language and accuracy passes are pending.

## E17 Completeness and backlog

Done and tested: schemas, ledger, judge, router, backends, literature pipeline, sentence statuses, audit, app, PDF, showcase. Done, no baseline beaten: research loop (command line). Planned only, closed as not planned: P1 on external papers, the ScientistTwo batch audit, the portfolio papers, asking the reference about every claim at write time, multi-run measurement, a person's labels, experiments from the app, an independent user.

Backlog (Fix): add pytest and ruff to CI; correct documents (S7); correct gate-state attribution; re-run planted-fault test on current code. (Improve): case-insensitive wording rules; person's labels on a sample. (Add): one outside walkthrough; hosted deployment only if the local-only decision is reversed. Next milestone: CI runs the tests and fails on a break (exit test: a deliberately broken test makes the workflow fail). Then: re-run the planted-fault measurement; then labels on a sample.

## Diagram sources

Images in `images/VERA-*.png` were drawn with a small matplotlib script (boxes and arrows) kept in the session scratch folder; no raw diagram code is in the Explainer. Chart values: judge agreement 79/86/89, 93/93/95, 77/87/89 (from `judge8_test.json`); real-text checks 0/21, 15/21, 2/69, 14/69 (from `realcase_incr7_test.json`). The journey picture uses toy confidence numbers.

## E18 Revision log (v1 draft to v2, reader-check fixes, 2026-10-27)

Previous version archived as `VERA.v1draft.md` (7,426 words). New version about 7,170 words by plain `wc -w`. Fixes from `VERA.readercheck.md`:

1. Length: models chapter cut from about 1,400 to about 900 words as a narrative; test counts, per-model prices, tokens-per-million, sampling detail and the "prompts and handling" list removed; recruiter table cut from 8 rows to 6 and from 5 columns to 3. No new facts were added; all numbers are those already sourced in E1 to E17.
2. Opening: ScientistTwo, Meridian, Jev, GLM and "reference judge" are no longer used undefined in the opening; ScientistTwo is defined in the problem chapter, Jev, GLM and the reference judge in the worked example, Meridian at first use in the problem chapter.
3. Same as fix 3, plus "increment" (ten numbered build stages) and "gate" (a checkpoint) defined in the build chapter; later chapters say "build stage" or "checkpoint".
4. The likelihood-ratio example replaced by a plain medicine-dropped-condition example in the problem chapter, and a toy "error rate known exactly / only estimated" example in the walkthrough, labelled toy.
5. Models chapter now opens with the three-model summary (one writer, one cheap checker, one strong checker).
6. Confidence defined in plain words (0 to 1; 0.5 is a coin-flip lean) before the worked example; the 0.7 threshold explained as "too unsure".
7. Edge-case table replaced by prose plus the two "partly" cases; "how it is known" column dropped. The separate results prose table duplicate merged into one results table with the caveat column.
8. 99.8 and 97 percent (easy items) reconciled with 89, 95, 89 (real items) in the models chapter in one sentence.
9. 50 of 52 caveat (earlier audit version, 3 of 6 controls failed) and "only claim sentences are tied to quotes" stated in the opening; tagline changed to the exact three sentence kinds.
10. Glossary expanded (calibration, confidence, evaluator, gate, GLM, increment, OpenRouter, paper databases, ScientistTwo, temperature, token). "Honest" self-assessment wording removed (headings, in-short lines, recruiter lines).

Also removed: the "Typical requirement" columns "What the project shows"; the DeepSeek/MiMo/Gemma percentage list (now one sentence; figures remain in E6/E12); the sentence about Dependabot and branch protection; local scratch-folder wording ("scratch copy" now explained as a throwaway copy). Test-count detail (828 passed/4 skipped without Docker, 851 with) kept here in E7, not in the guide. Not published.

# SPEC — VERA, Increment 5 (the app: UI/UX and bring-your-own-key)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 5; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.10, with v0.11 proposed where
a feature needs it; requirements due: APP-F-01, APP-F-02, APP-C-01, APP-C-02,
plus everything due earlier ([docs/02-requirements.md](docs/02-requirements.md));
trades to decide: **T8** (app delivery and bring-your-own-key), and the
reverse-ifs this increment first tests: T9 (2) (a reasoning control that makes a
cheaper model usable), T1 (1) again on larger N, T5 (5) (a second keyed source)
([docs/04-trade-studies.md](docs/04-trade-studies.md)). Rewrite this file at each
increment review. The Increment 4 SPEC is in git history; its review is
[docs/reviews/incr-4.md](docs/reviews/incr-4.md).

The goal is unchanged: **very good research on whatever topic is requested**, not
novel research. Increment 4 measured where the loop stands and the answer was
plain: the pipeline is cheap ($3.18 spent of $9 across the whole increment; about
$0.10 per loop run) and candid, its literature reviews scored 3 to 4 on most
criteria, its two papers scored lower (tree-explain 4,3,2,5,5 and credal 3,2,2,5,5
on Chris's rubric), no idea beat a baseline, the audit caught two real
misstatements and failed 3 of 6 clean controls, retrieval pooled recall is 59%
(34 of 58 key papers), and the audit's freeze was broken after its test runs. This
increment does **not** try to fix research quality wholesale. It makes what exists
usable by a person who is not Chris, with their own key and their own money, and
spends a bounded share on the carry-ins that make the app's output more
trustworthy to read.

The product, one step wider: a **local web app** (T8 leaning (a); see the decision
below) with a landing page that says in plain words whose key and money are used and
what a run typically costs (measured, from the ledgers); a place to connect a key; a
run form (topic, output guidance, budget); a live view of stage progress, verdicts and
spend read from the run's ledger; a paper reader with evidence links (each claim to its
quote, each number to its results cell); stop and resume. No maintainer key in any
shipped artifact. Exit (docs/07): **a new user completes S4 through the app with their
own key** (MOE-4).

Who does what: Claude Code builds and runs short work; Chris decides T8, supplies and
holds his own key, approves human gates himself (the agent reports readiness and never
approves for him), finds or is the new user for the S4 walkthrough, reads and edits the
landing-page wording, and scores the outputs. Chris launches long runs from his own
terminal or the app.

Rules carried from the Increment 4 review:

- **Spend.** Every model call goes through a `Budget` that raises before a limit is
  crossed, inside the $20/month ceiling (ConOps §4). Proposed caps for Chris to confirm
  at `incr5_scoped`: **$1** for debugging and smoke runs; **$3** for end-to-end runs
  through the app (one literature-only run and one run with experiments, and the new
  user's run, which is billed to the user's own key and not counted, but a maintainer
  dry run of the same path is); **$1.50** for the judge on a larger labelled set and the
  T9 (2) reasoning-control test; **$5** for the increment, each calendar month inside
  $20. Increment 4 spent $3.18 of its $9.
- **One ledger file per run**, `data/ledger/run_<run_id>.jsonl`, never deleted, truncated
  or overwritten. The app reads this file for live spend and writes nothing to it that a
  run did not.
- **Independence and freezing.** The audit's source tree is frozen at its Increment 4
  hash for the audit-v3 test sets; **this increment changes no frozen audit file** unless
  it spends a new test set first (a new seeded set, built before the change, is part of
  that decision, not a quiet side effect). The scoping of the method-code check is one
  such change and is listed below with its cost.
- **Human scoring is blind and attributed**, helper labels disclosed. Provenance of every
  human score and label is recorded as given (who, when, whether a model assisted).
- **Secrets.** APP-C-01/02: no maintainer key in the repository, any build artifact, any
  log, any ledger, any cached page; none reaches the sandbox; the user's key is held in
  the server process memory (or the environment) only, never written to disk, never
  echoed to the browser after entry, never in a URL. `tests/test_no_secrets.py` stays and
  is extended to the app.
- **Dogfood.** Overhead hours are logged **at the end of every session**
  (`scripts/overhead-due.sh` prints the command). The check credits a day named at the
  start of an entry's note (Chris, 2026-10-05).
- **Outward-facing actions** need Chris: a public hosted deployment, a pushed commit,
  a request to a bibliographic service beyond polite keyless use.

Gate DAG proposed for `.meridian/gates.yaml` after `incr5_scoped`:

```text
incr4_review ─► incr5_scoped ─┬─► carry5_ready ──────────────────────────────────┐
                (human)       │   (automated: judge N, checks, T9 (2) test)      │
                              ├─► t8_decided ─► app_core_ready ─► ui_ready ──────┤
                              │   (human)       (automated:       (automated:    │
                              │                  API, runs, key)   UI, landing)  │
                              └─► key_safety_ready (automated; needs app_core) ──┤
   ┌─────────────────────────────────────────────────────────────────────────────┘
   └─► newuser_walkthrough ─► rubric5_scored ─► incr5_review
       (human: S4, own key)    (human, blind)    (human + Evaluator)
```

## Carry-in: checks and measurements from the Increment 4 review

`vera/loop/`, `vera/audit/`, `tools/checks/`, `data/`. Built and tested offline first.

- **Overhead per session.** Already enforced; nothing to build beyond using it.
- **Degenerate-spread check** (new, `vera/loop/`, not an audit file): an idea whose
  results have a spread of zero or near zero (1e-13 to 1e-5 across 100 replications in
  the credal run) is flagged invalid at the results gate, with the reason, before it is
  written up as a result. Rule, not a judge.
- **Method-code check scoped to the sentences about the idea** (AUD-F-05): the Increment 4
  check raised a warning on 4 of 6 clean controls. Scoping it is a change to a frozen
  audit file and **spends the audit v3 test sets**. The decision is Chris's at
  `incr5_scoped`: either (i) make the change, build seeded set v4 and measure it the way
  v3 was measured (dev/test by source, freeze before the test run), or (ii) leave the
  check as a lead for a person and say so in the app's audit panel. Recommendation: (ii)
  in this increment, because the app shows a warn as "a lead, not a verdict" and the
  rebuilt test set is the largest cost in the list.
- **The judge on a larger labelled set** (T1 reverse-if (1), interval stated): at least
  150 labelled decisions on the loop's gates, interval reported, cost within the cap.
- **A second keyed source** (T5 reverse-if (5), fired by both scorers' coverage scores):
  Semantic Scholar through the user's own key when supplied, never a maintainer key, and
  the stage works unchanged when none is supplied. Recall remeasured on the six topics
  and reported against the 59% pooled; the key lists are not changed.
- **T9 reverse-if (2), a reasoning control:** test whether a setting that bounds
  reasoning (per-provider control through OpenRouter) lets GLM-5.3 Flash or one of the
  failed arms produce valid experiment code at a lower cost than Sonnet 5.5. Same
  protocol as the Increment 2 comparison (3 repeats from the same recorded baseline).
  The result decides what the app offers as its low-cost model; it is not required to
  succeed.
- **Credal ideas that run correctly** is *not* in this increment: the loop's credal ideas
  were far worse than the baseline with implausibly small spreads; the degenerate-spread
  check above stops them being reported as results. Diagnosing them is Increment 6 or later.
- **Chris's own labels for the ten novelty ideas** are optional: if he supplies them, the
  agreement is recomputed. Otherwise the review keeps saying those labels are the model's,
  adopted by him.

**Acceptance:** `tools/checks/check_carry5.py`: the spread check has a test with a planted
near-zero spread; the judge result file has at least 150 decisions with the interval; the
second-source recall table exists with the old and new figures; the T9 (2) result is
committed with every run's ledger; spend within the cap; no frozen audit file changed
(hash compared) unless the decision above was (i) and its seeded set exists.
**Gate:** `carry5_ready`.

## T8: how the app is delivered (human decision)

`docs/04-trade-studies.md`. The trade is open since Increment 0 with a leaning. Chris
decides it after the agent measures what the options cost:

- **(a) Local app**, localhost web UI, the user's key in their own environment or pasted
  into the page and held in process memory. The experiment stage needs Docker for the
  sandbox, so the app's first-run checklist says whether Docker is present and what is
  available without it (the literature stage and a paper from the literature alone need
  no Docker).
- **(b) Hosted demo**: a public site. BYOK moves model spend to the visitor but not
  sandbox compute or hosting, and a hosted app has to hold a visitor's key for the length
  of a run (APP-C-02 says not stored server-side). A hosted demo would run the literature
  stage only.
- **(c) Both**, local as the product and hosted as the demo.

Measured before the decision: the cost of a literature-only run per topic from the ledgers
(Increment 3 and 4: $0.14 to $0.22 on Sonnet 5.5), the cost of a run with experiments,
and the cost of hosting a literature-only demo per visitor under a hard cap (a design
estimate; nothing is deployed). Recommendation: **(a) only in this increment** and (c)
reconsidered at the review; a public deployment is an outward-facing action and is not
built here. If Chris picks (c), the hosted part is its own gate and scope change.

**Acceptance:** a **Scores / Decision / Reverse if** entry in docs/04 with the measured
costs, written before the decision.
**Gate:** `t8_decided` (human approval, token "T8 DECIDED").

## The app core: runs, ledger, key

`vera/app/`. A small server (FastAPI, since the project is Python and the loop is
callable as a function) with a thin JSON API and server-sent events for progress. No
framework build step on the front end (plain HTML, a small amount of vanilla JS or HTMX),
so it runs on Windows with `uv run vera-app` and nothing else installed.

- **Runs as the user's process, not a shared service.** `POST /runs` starts the existing
  runner (`scripts/run_loop.py` / the literature stage) as a subprocess with the key in
  its environment, a per-run directory, the budget and wall limits the form gave, and
  returns the `run_id`. A run survives the page closing; **stop** sends a clean stop the
  runner honours at its next stage boundary (so the ledger is consistent) and **resume**
  restarts from the last completed stage (the loop's `retry_from`).
- **Live view:** the ledger and gate files already carry everything the UI shows: stage
  entered, stage verdict (pass, fail, confidence, backend), cumulative spend against the
  budget, wall time. The API only reads them; it computes nothing a run did not record.
- **Key handling:** the key is accepted in a POST body, validated by one inexpensive call
  (model list or a one-token completion, ledgered as a validation), held in process memory,
  passed to the child process through its environment, never logged, never returned. The
  server binds to 127.0.0.1 only; a cross-origin request is refused. If the key is in the
  environment the app says so and never asks for it. A "forget key" button clears it.
- **Budget form:** a dollar cap (default and maximum shown with a plain note on typical
  cost), a wall limit, output guidance (format, length, emphasis, constraints), and whether
  experiments are allowed (needs Docker; shown as unavailable with the reason if it is not
  found). The cap goes into the `Budget`; the loop never raises it.
- **Schemas 0.11 (docs/03 first):** `RunRequest` (topic, guidance, budget, wall limit,
  allow_experiments, run_id), `RunStatus` (stage, state, spend, limit, started, updated,
  last verdict), `AppConfig` (docker available, key source: `env` or `session`, never the
  key).

**Acceptance:** tests offline with a fake runner and a fake model: a run starts, streams
stages, stops at a boundary with a consistent ledger and resumes; the budget form's cap is
what the `Budget` enforces; a request from another origin is refused; the API never returns
the key; `test_APP_F_01_…` and `test_APP_C_02_…` exist and pass.
**Gate:** `app_core_ready`.

## Key safety (APP-C-01, APP-C-02)

`tests/`, `tools/checks/check_app_secrets.py`. A feature of its own because it is the one
thing the user trusts without being able to see.

- A scan of the repository, the built app, every log and ledger a test run produces, and
  the browser-facing responses for any string shaped like a key (the OpenRouter prefix and
  the others the project has ever used) and for the actual test key used in the run.
- An adversarial test: a key with a distinctive marker is entered, a run is made, and the
  marker must appear in **no file under the data, log or ledger directories**, no response
  body, no process command line, and no exception message.
- A statement in the landing page and README of exactly what is held where, checked by a
  test that the wording matches the behaviour (for instance, "kept in memory only" is
  tested by the scan above).
- Windows specifics checked by hand once: the key is not in the environment of the
  sandbox container (checked with `docker inspect`), nor in the process list.

**Acceptance:** `check_app_secrets.py` passes on the repo and the test artifacts;
`test_APP_C_01_…` and `test_APP_C_02_…` exist; the sandbox container's environment is
shown to carry no key.
**Gate:** `key_safety_ready` (requires `app_core_ready`).

## UI/UX: landing page, run form, live view, reader

`vera/app/static/`. Attractive and functional, designed for a person who has never seen the
repo. Text written for that person, not for Chris: plain words, no gate or audit jargon on
the front page, the audit shown as a traffic light with one sentence per item and the full
audit one click away.

- **Landing page:** what VERA does in two sentences; **whose key and money are used**
  (the visitor's; the maintainer pays nothing and has no access); what a run typically costs
  with the measured range from the ledgers and the statement that a run can end without a
  better method, which is normal; what it will not do (no wet-lab, no proprietary data,
  CPU-scale experiments only); a "connect key" step and a first-run checklist (key found,
  Docker found, disk space).
- **Run form and live view:** topic box with a "see the question VERA will research"
  confirmation step (the scoping stage's output shown for the user to accept or edit, as
  S4 requires), progress by stage with its verdict, spend against the cap as a bar, stop and
  resume, and an honest "stopped at budget: best so far" state.
- **Paper reader:** the paper-shaped write-up rendered with figures; each cited claim opens
  its quote and source link; each table cell and number opens its `results.json` cell; the
  audit panel states green, amber or red in words, including "a warning is a lead, not a
  verdict" for the method-code check and the novelty check.
- **Accessibility and basics:** keyboard use, readable contrast in light and dark, a phone
  width layout, no external scripts on the front page beyond what is bundled.
- **No claims the data does not support:** the landing page's cost figures and the quality
  statement are generated from files (the ledgers and the rubric summary), not typed, so
  they change when the evidence does. A test checks the page contains no number that is not
  in its source file.

**Acceptance:** screenshots of each screen in light and dark and at a narrow width are
committed; `tests/test_app_ui.py` renders each page against fixture runs (a finished run,
a stopped run, a budget-exhausted run, a red audit) without error; the landing-page
numbers test passes.
**Gate:** `ui_ready` (requires `app_core_ready`).

## The new-user walkthrough (MOE-4, human)

The increment's exit is a person other than the builder doing S4. Chris decides who: a
person who has not seen the repo (preferred), or Chris himself from a fresh clone on a
machine or user account with no project files, stated in the review as a weaker test.
They are given the repository link, a README, and their own OpenRouter key with a small
credit; they are **not coached**. An observer (Chris or the agent) records, without
helping, each point of confusion, each time they stop, and the time to a first finished
literature-only run and to a run with experiments if Docker is available. Afterward the
person answers: did the landing page tell you whose money was used; did you trust the
spend display; was the paper worth reading; what would you not use.

The run uses the user's own key and money, so its spend is the user's; the maintainer's
ledger copy of the run is kept as the evidence, with the key never in it.

**Acceptance:** `tools/checks/check_newuser.py`: the observation record (who, when, from
what state, what was shown), the run's ledger and report, the time taken, and the person's
answers exist; the run completed inside the budget the person set; the record states
whether the person is independent of the builder.
**Gate:** `newuser_walkthrough` (human approval, token "NEW USER WALKTHROUGH"; requires
`ui_ready` and `key_safety_ready`).

## Rubric scoring of the app's output (human, blind)

The same five criteria, scored 1 to 5 by Chris before he reads any other scorer's, with
`--blind`, on **the outputs a new user actually receives**: the walkthrough's paper or review
and two more produced through the app on topics Chris chooses (one empirical, one not). An
independent scorer follows. Chris's own provenance note is recorded as given (including any
assistance by another model, which Increment 4 recorded after the fact).

**Acceptance:** `tools/checks/check_rubric.py` adapted to the new files: every output has an
entry by a named human marked blind and recorded before the independent scorer's file; the
entries differ from the independent scores in some cell; a provenance field is present.
**Gate:** `rubric5_scored` (human; requires `newuser_walkthrough`).

## Increment 5 review

Write `docs/reviews/incr-5.md` against the docs/07 exit criterion: a new user completes S4
through the app with their own key. Also: the T8 decision and its measured costs; the
walkthrough's confusions and what the app does about each; the key-safety evidence and its
limits; the carry-ins closed or restated (the judge's interval on larger N, the second keyed
source's recall against 59%, the T9 (2) outcome, the spread check, the method-code decision);
rubric scores of both scorers against Increment 4's; the audit freeze status; spend against the
caps; per-session overhead; same-model overlap; deviations; and what Increment 6 takes (P1 on
external papers) or whether the project stops here. Keep it factual and unflattering.

**Acceptance:** `check_dogfood.py` finds an overhead entry recorded after the last review gate
for each calendar day a gate passed; the review passes the independent Evaluator
(`run-evaluator.sh`), fresh per round, every verdict kept, the review's numbers checked
against the ledgers and result files.
**Gate:** `incr5_review`.

## Decisions for Chris at incr5_scoped

1. The caps above ($1 / $3 / $1.50 / $5, inside $20 a month).
2. T8's direction going in: local only (recommended) or local and a hosted demo (a larger
   scope; the hosted part would be its own gate).
3. The method-code scoping: leave as a lead and say so (recommended), or spend the test sets
   and build v4.
4. Who is the new user for the walkthrough, and whether a key and a small credit can be
   arranged for them.
5. Whether Increment 5 includes the second keyed source (Semantic Scholar; needs a user key
   for the test) and the T9 (2) reasoning test, or either is dropped to protect the app work.
6. Read: this SPEC and the Increment 4 review's open items (judge on larger N, broken freeze,
   rubric provenance, retrieval recall).

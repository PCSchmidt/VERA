# CLAUDE.md — working instructions for this repo

Read `README.md` first, then the doc relevant to your task in `docs/`.

## Context

- Owner: Chris, ML engineer; applied-math background; builds agentic harnesses
  (see Meridian — generator/evaluator separation, gated DAG checkpoints).
- This is a personal portfolio/research project. Keep it fully separate from
  employer work, data, and systems.
- Dev environment: Windows + VS Code + Claude Code. Use cross-platform paths
  (`pathlib`), no bash-only scripts unless also provided for PowerShell.
  **Exception:** Meridian's harness files (`scripts/*.sh` installed by Meridian,
  `.claude/hooks/`, the git `pre-commit` hook) are Bash and run under Git Bash.
  VERA's own scripts are Python (`scripts/*.py`). The only VERA `.sh` files are
  one-line gate wrappers (`scripts/gate-*.sh`) that call the Python checks in
  `tools/checks/`, because Meridian runs gate hooks with bash.

## Meridian (build harness)

- Gates: `.meridian/gates.yaml`. Scope contract: `CONTRACT.md`; current
  increment features: `SPEC.md`. `docs/` stays the source of truth.
- Check where you are: `bash scripts/gate-engine.sh current`, then
  `bash scripts/gate-engine.sh verify <gate>`.
- Automated gates: `bash scripts/gate-engine.sh mark-passed <gate>` (it re-runs
  the checks). **Human approval gates are Chris's to approve** in his own
  terminal; report readiness instead of trying to approve.
- Never edit `.meridian/gate-state.json` directly.
- Dogfood log: when a gate blocks, note it; Chris labels stops with
  `bash scripts/dogfood.sh label <n> real|false_alarm|unclear`.

## Source of truth

1. `docs/03-interfaces.md` defines the schemas. Code must match it. If code
   needs a schema change, propose the change in the doc first (bump version,
   add a changelog line) — do not silently diverge.
2. `docs/02-requirements.md` — every feature should trace to a requirement ID.
   Reference IDs in commit messages and test names (e.g. `test_AUD_F_03_...`).
3. `docs/07-increments.md` — work only on the current increment unless asked.

## Engineering rules

- Python 3.11+, `uv` for env/deps, Pydantic v2 for schemas, pytest for tests.
- Every judgment is a `Verdict`. Never return a bare bool/str from a judge.
- Every model call records cost, latency, backend, and trace ID to the ledger.
  An untracked model call is a bug.
- Judge backends sit behind the `JudgeBackend` protocol. No vendor SDK imported
  outside `backends/`.
- Agent-generated or third-party code runs only inside the sandbox, never in
  the host process.
- No self-grading: the component that produces an artifact never issues the
  verdict on it (Meridian principle). Tests should enforce this where possible.
- Budgets are hard limits. Exceeding a `Budget` raises; it does not warn.

## Data rules

- The ScientistTwo papers and parent papers are **evaluation data**. Store
  locally under `data/raw/` (gitignored). Do not commit or re-host PDFs.
- Record provenance (URL, retrieval date, hash) for every downloaded file.
- Health/medical datasets: public and de-identified only; respect license
  and credentialing terms.

## When unsure

Prefer a small, testable step and ask. Don't expand scope beyond the current
increment's exit criteria.

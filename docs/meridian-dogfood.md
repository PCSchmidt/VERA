# Meridian dogfood log (VERA)

VERA is Meridian's first measured "Full" dogfood. This file records findings
about Meridian itself. Per-stop labels, escapes, and overhead hours are
recorded with `bash scripts/dogfood.sh` (committed in `.meridian/dogfood.jsonl`);
`bash scripts/dogfood.sh report --md` summarizes them.

Comparison baseline: `sitework-ai`, built without Meridian but with its own
milestones and measured success criteria.

## Setup findings (2026-09-29)

Found while installing Meridian and writing VERA's Increment 0 gates. Each was
fixed in Meridian the same day.

| # | Finding | Impact | Fix (Meridian commit) |
|---|---------|--------|-----------------------|
| M1 | `mark-passed` recorded a gate without checking deps, artifacts, pre-hooks, or approval token; the agent could approve human gates | Human gates were honour-system | Gates must be earned; operator-only `--approve`; verify fails commits with unrecorded approvals (`65eab77`) |
| M2 | Declared pre-hooks that weren't installed were skipped with a warning, so the gate passed | 20 recipe hooks don't exist; HPI passed 4 gates whose checks never ran | Missing hooks block; `validate` warns up front (`65eab77`) |
| M3 | `run-evaluator.sh` blocked whenever used as a pre-hook (no gate id argument) | The Evaluator could never pass a gate through `verify` | `verify` exports `MERIDIAN_GATE_ID` (`65eab77`) |
| M4 | Hook blocks reached only `hooks.log`; commit-time events all had session `00000000`; some reasons silently dropped as invalid JSON | No usable dogfood data (HPI: 198 verify runs, 1 block, no evaluator verdicts) | `hook_blocked` telemetry, real session ids, JSON escaping, `dogfood.sh` (`edb4ff5`) |
| M5 | Windows `jq` emits CRLF; list values kept a stray `\r` | Artifact paths and deps silently mismatched | Strip `\r` (`65eab77`) |
| M6 | Shell scripts not pinned to LF | Fresh Windows clones with autocrlf would break every hook | `.gitattributes` (`ec4dd43`) |
| M7 | `install.sh` copied a runtime `hooks.log` from the source hooks dir | Stray file committed into VERA | Installer removes it (`7e70722`) |

Open, minor:

- `install.sh` without `--recipe` says "gates.yaml not installed" even when the
  project already has one.
- Hook output starts with "Hook wrapper loaded for unknown": hooks set
  `HOOK_NAME` after sourcing the wrapper.
- Gate hooks run with no arguments, so a check needing a parameter (T3 for the
  parser trade) needs its own wrapper script.

## Spec review (independent Evaluator, before `confirmed`)

The first draft of CONTRACT/SPEC **failed** the fresh-context spec review
(`.meridian/evaluator/spec-review.json`): 2 high, 15 medium, 6 low gaps and 6
contradictions. Both high gaps (undefined data source; spend ceiling unset so
`confirmed` could never pass) were real. Fixed before approval.

## Gate log

| Date | Gate | Result | By |
|------|------|--------|----|
| 2026-09-29 | `confirmed` | passed (3/3 checks) | Chris (approval recorded) |
| 2026-09-29 | `scaffold_ready` | passed first try (ruff clean, 68 tests, schema 0.2 = docs/03) | agent (automated gate; `mark-passed` re-ran the checks) |

## Observations

- Writing the schemas surfaced a spec gap no gate could catch: docs/03's
  `Budget` had `max_model_calls` but no call counter, so `charge()` couldn't
  enforce it. Fixed by the documented process (docs/03 → v0.2 with a changelog
  line). The schema-version check then forced code and doc to move together.

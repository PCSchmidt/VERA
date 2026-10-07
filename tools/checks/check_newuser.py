# ruff: noqa: E501
"""Gate `newuser_walkthrough` (before Chris approves): a person used the app for S4 with their own key, and the session is on record.

Requires `data/walkthrough/record.json` (template: record.template.json) with: who (a name or role), whether the person is independent of
the builder (stated either way), what state they started from, the observer, `coached: false`, when the session and the first run started
and when it finished, the run id, a confusion log (possibly empty, each entry with where and what), and non-blank answers to the four
questions; and the run's evidence in `data/walkthrough/<run_id>/` (scripts/collect_walkthrough_run.py): final state `complete`, the review,
its audit report, and a ledger whose total is within the cap the person set. Reports the time to a finished run, the number of confusions and
how many the observer helped with; a session where the person was coached is not a walkthrough.
"""

from __future__ import annotations

import datetime as dt
import json

from _common import block, ok, repo_root_arg

ANSWERS = ("whose_money_and_how_they_know", "trusted_the_spend_display_and_why", "review_worth_reading_and_what_better",
           "what_would_stop_them_using_it")  # fmt: skip


def when(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    path = root / "data" / "walkthrough" / "record.json"
    if not path.exists():
        block("data/walkthrough/record.json not found (copy record.template.json and fill it in after the session)")
    rec = json.loads(path.read_text(encoding="utf-8"))
    for field in ("person", "setup", "observer", "key_provided_by", "run_id"):
        if not isinstance(rec.get(field), str) or not rec[field].strip() or rec[field].startswith(("a first name", "from what state")):
            block(f"record.json: {field!r} is missing or still the template text")
    if not isinstance(rec.get("independent_of_builder"), bool):
        block("record.json: independent_of_builder must be true or false (state it either way)")
    if rec.get("coached") is not False:
        block("record.json: coached must be false; a session where the person was helped is not a walkthrough")
    try:
        started, first, finished = (when(rec[k]) for k in ("started_at", "first_run_started_at", "finished_at"))
    except (KeyError, ValueError):
        block("record.json: started_at, first_run_started_at and finished_at must be ISO times")
    if not started <= first < finished or started.year < 2026 or started.month == 0:
        block("record.json: the times are not in order, or still the template values")
    confusions = rec.get("confusions")
    if not isinstance(confusions, list) or not all(isinstance(c, dict) and c.get("where") and c.get("what") for c in confusions):
        block("record.json: confusions must be a list (empty if none) of entries each with 'where' and 'what'")
    answers = rec.get("answers") or {}
    if any(not str(answers.get(a, "")).strip() for a in ANSWERS):
        block("record.json: all four answers must be filled in")

    evidence = root / "data" / "walkthrough" / rec["run_id"]
    for name in ("app_request.json", "app_state.json", "literature.md", "audit_report.json", "ledger.jsonl"):
        if not (evidence / name).exists():
            block(f"data/walkthrough/{rec['run_id']}/{name} not found (scripts/collect_walkthrough_run.py)")
    state = json.loads((evidence / "app_state.json").read_text(encoding="utf-8")).get("state")
    if state != "complete":
        block(f"the person's run ended '{state}', not 'complete'")
    cap = json.loads((evidence / "app_request.json").read_text(encoding="utf-8"))["max_usd"]
    spent = sum(json.loads(ln)["cost_usd"] for ln in (evidence / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip())
    if spent > cap:
        block(f"the run spent ${spent:.4f}, over the cap the person set (${cap})")
    minutes = (finished - first).total_seconds() / 60
    helped = sum(1 for c in confusions if c.get("observer_helped"))
    ok(f"{'independent' if rec['independent_of_builder'] else 'NOT independent of the builder'} walkthrough by {rec['person']}; "
       f"a finished run in {minutes:.0f} minutes for ${spent:.3f} of a ${cap} cap; {len(confusions)} confusions logged, observer helped with {helped}")


if __name__ == "__main__":
    main()

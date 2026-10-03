"""Gate `incr2_review`: Meridian overhead was logged for every calendar day on which a gate passed this increment.

Usage: check_dogfood.py [--since-gate <gate>]

Gate passes come from `.meridian/telemetry.jsonl` (`gate_passed` events after the `--since-gate` gate passed, which
opens the increment; by default the most recent `incr<N>_review` gate passed, so the check needs no editing per
increment); overhead entries from `.meridian/dogfood.jsonl` (`type: overhead`, written by
`scripts/dogfood.sh overhead <hours> [note]`). Days are UTC calendar days, as both files stamp them. A day passes if
at least one overhead entry with positive hours was recorded on it **after the increment opened** (entries recorded
before it do not count: one carried-over entry cannot satisfy a new increment's first day, the Increment 3 loophole).
The check reads the day an entry was recorded, not the work it covers: an entry logged at the end of a session for
several days covers only that day here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from _common import block, ok, repo_root_arg


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(ln))
        except ValueError:
            continue
    return rows


REVIEW_GATE = re.compile(r"incr\d+_review")


def latest_review_gate(telemetry: list[dict]) -> str:
    """The most recent increment review gate that passed: the one that opened the current increment."""
    passed = [e for e in telemetry if e.get("event_type") == "gate_passed"]
    reviews = [e for e in passed if REVIEW_GATE.fullmatch(e.get("gate", ""))]
    if not reviews:
        block("no incr<N>_review gate has passed in the telemetry; cannot tell where the increment starts")
    return max(reviews, key=lambda e: e["timestamp"])["gate"]


def gate_days(telemetry: list[dict], since_gate: str) -> tuple[dict[str, list[str]], str]:
    """Gates passed after `since_gate`, by UTC day, and the time the increment opened."""
    passed = [e for e in telemetry if e.get("event_type") == "gate_passed"]
    opened = [e["timestamp"] for e in passed if e.get("gate") == since_gate]
    if not opened:
        block(f"gate {since_gate!r} has no gate_passed event in the telemetry; cannot tell where the increment starts")
    start = max(opened)
    days: dict[str, list[str]] = {}
    for e in passed:
        if e["timestamp"] > start:
            days.setdefault(e["timestamp"][:10], []).append(e["gate"])
    return days, start


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--since-gate", default=None, help="default: the latest incr<N>_review gate passed")
    args = parser.parse_args()
    telemetry_file = args.root / ".meridian" / "telemetry.jsonl"
    dogfood_file = args.root / ".meridian" / "dogfood.jsonl"
    if not telemetry_file.exists():
        block(".meridian/telemetry.jsonl not found; gate-pass days cannot be read")
    telemetry = read_jsonl(telemetry_file)
    since_gate = args.since_gate or latest_review_gate(telemetry)
    days, start = gate_days(telemetry, since_gate)
    entries = [e for e in (read_jsonl(dogfood_file) if dogfood_file.exists() else []) if e.get("type") == "overhead"]
    by_day: dict[str, list[dict]] = {}
    before = 0  # entries recorded before the increment opened: a carried-over entry cannot cover a new increment's day
    for e in entries:
        if (e.get("hours") or 0) > 0:
            if e["recorded_at"] < start:
                before += 1
                continue
            by_day.setdefault(e["recorded_at"][:10], []).append(e)
    missing = sorted(d for d in days if d not in by_day)
    if missing:
        block(
            f"no overhead entry recorded after {start} on {missing} (gates passed: {[days[d] for d in missing]}; "
            f"{before} earlier entries do not count); log it at the end of the session: "
            "bash scripts/dogfood.sh overhead <hours> <note naming the dates and work>"
        )
    lines = []
    for day in sorted(days):
        hours = sum(e["hours"] for e in by_day[day])
        lines.append(f"{day}: {len(days[day])} gates, {hours:g} h in {len(by_day[day])} entries")
    if before:
        lines.append(f"{before} entries recorded before the increment opened were not counted")
    ok(f"overhead entry for every day a gate passed since {since_gate} ({start}): " + "; ".join(lines))


if __name__ == "__main__":
    main()

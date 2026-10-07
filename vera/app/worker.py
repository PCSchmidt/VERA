"""One phase of one run, as its own process: `python -m vera.app.worker <run_id> <start|continue|resume>`.

The server starts this with the user's key in the environment. The worker records what it is doing in
`runs/<run_id>/app_state.json` (a state word and a message, never anything secret) and exits; the long work happens here
so a closed browser tab, or a stopped server, does not end the run.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from vera.app import state as app_state
from vera.app.pipeline import real_deps, run_audit, run_phase
from vera.backends import redact
from vera.keepawake import keep_awake
from vera.schemas import BudgetExceeded, RunRequest

ROOT = Path(__file__).resolve().parents[2]


def finish_state(final: dict, phase: str) -> tuple[str, str | None]:
    stop = final.get("stop")
    if not stop:
        return "complete", None
    reason = stop.get("reason", "")
    if reason.startswith("awaiting confirmation"):
        return "awaiting_confirmation", "Check the question VERA proposes, then confirm it or edit it."
    if "stopped by the user" in reason:
        return "stopped", "Stopped at your request. Everything done so far is kept; you can resume."
    if reason.startswith("budget:"):
        return (
            "stopped",
            f"Stopped at your budget ({reason}). The best result so far is kept; resuming needs a higher cap.",
        )
    return "failed", f"Stopped at {stop.get('stage')}: {reason}"


def main(argv: list[str], root: Path = ROOT) -> int:
    run_id, phase = argv[0], argv[1]
    run_dir = root / "runs" / run_id
    request = RunRequest.model_validate_json((run_dir / "app_request.json").read_text(encoding="utf-8"))
    app_state.write(run_dir, "scoping" if phase == "start" else "running", None)
    try:
        deps = real_deps(root, request, resume=phase != "start")
        with keep_awake():
            final = run_phase(deps, phase)
        state, message = finish_state(final, phase)
        if state == "complete":
            try:
                run_audit(deps)
            except BudgetExceeded:
                message = "The review is finished but the final audit did not fit in your budget; it is not audited."
    except Exception as exc:  # noqa: BLE001 - the user is told in words; the traceback goes to the run's own log
        (run_dir / "worker_error.log").write_text(redact(traceback.format_exc()), encoding="utf-8")
        state, message = "failed", f"The run could not continue: {type(exc).__name__}: {redact(str(exc))[:300]}"
    app_state.write(run_dir, state, message)
    print(json.dumps({"run_id": run_id, "state": state}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

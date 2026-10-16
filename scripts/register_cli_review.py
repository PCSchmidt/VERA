# ruff: noqa: E501
"""Register a review made from the command line (Increment 4) with the local app, so a review paper can be made from it.

    uv run python scripts/register_cli_review.py <run_id> --topic-file data/topics/<id>.json --guidance-from <example id>

The app's paper step (APP-F-04) continues a finished review's own checkpoint thread, ledger and passages; a command-line
review has all three but not the two small files the app reads: `app_request.json` (the request, rebuilt from the topic
file and the guidance and cap the Examples page lists for it) and `app_state.json` (state "complete"). This writes those
two files and nothing else; it refuses a run that already has them, one whose scope is not confirmed, and one whose audit
failed. No model call. Used 2026-10-16, after the close, at Chris's request, for `topic4-conformal-2` and `topic4-agents-1`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera.app import state as app_state
from vera.schemas import RunRequest

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    ap.add_argument("--topic-file", required=True)
    ap.add_argument("--guidance-from", required=True, help="the example id in data/app/showcase.json")
    args = ap.parse_args()
    run_dir = ROOT / "runs" / args.run_id
    if (run_dir / "app_request.json").exists() or (run_dir / "app_state.json").exists():
        raise SystemExit(f"{run_dir} is already registered with the app")
    scope = json.loads((run_dir / "scope.json").read_text(encoding="utf-8"))
    if scope.get("status") != "confirmed":
        raise SystemExit("the review's question was never confirmed")
    light = json.loads((run_dir / "artifacts" / "audit_report.json").read_text(encoding="utf-8")).get("overall")
    if light not in {"green", "amber"}:
        raise SystemExit(f"the review's audit is {light}; a paper is made only from a review whose audit did not fail")
    spec = next(e for e in json.loads((ROOT / "data" / "app" / "showcase.json").read_text(encoding="utf-8"))["examples"]
                if e["id"] == args.guidance_from)  # fmt: skip
    topic = json.loads((ROOT / args.topic_file).read_text(encoding="utf-8"))["text"]
    request = RunRequest(run_id=args.run_id, topic=topic, guidance=spec["guidance"], max_usd=spec["budget_cap_usd"],
                         max_wall_seconds=7200)  # fmt: skip
    (run_dir / "app_request.json").write_text(request.model_dump_json(indent=1), encoding="utf-8")
    app_state.write(run_dir, "complete", None)
    print(f"registered {args.run_id}: {light} review, guidance from {args.guidance_from}")


if __name__ == "__main__":
    main()

"""Run a topic's literature stage again under Chris's earlier confirmation of the same question (lit2_ready).

The Increment 3 topics (tree-explain, credal-dro, llm-judge-numbers) are re-run through the v2 stage (12 queries over
seven angles, claim anchoring, retrieval note) to report their recall again. The scoped question is not asked of Chris
again: this script starts a new run, replaces the proposed scope with the question he confirmed for the topic
(`data/topics/scope_<topic>.json`, with his name and time of confirmation and a `reused_from` entry saying so), and
continues. The result is reported as not independent of the earlier runs (the key lists were known when the stage was
tuned).

Usage: uv run python scripts/relit_topic.py --topic tree-explain --run-id lit2-tree-explain [--max-usd 1.0]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "run_topic.py"), *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--max-usd", default="1.0")
    ap.add_argument("--skip-start", action="store_true", help="the run was started (its scope is replaced)")
    args = ap.parse_args()
    common = ["--topic", args.topic, "--run-id", args.run_id, "--max-usd", args.max_usd]
    if not args.skip_start:
        start = run(*common, "--phase", "start")
        print(start.stdout[-400:], start.stderr[-400:])
    old = json.loads((ROOT / "data" / "topics" / f"scope_{args.topic}.json").read_text(encoding="utf-8"))
    if old.get("status") != "confirmed" or not old.get("confirmed_by"):
        raise SystemExit("the topic's earlier scope was not confirmed by a person")
    scope_file = ROOT / "runs" / args.run_id / "scope.json"
    proposed = json.loads(scope_file.read_text(encoding="utf-8"))
    scope = {k: old[k] for k in proposed if k in old} | {
        "status": "confirmed", "confirmed_by": old["confirmed_by"], "confirmed_at": old["confirmed_at"],
        "reused_from": old["run_id"], "proposed_this_run": proposed["question"],
    }  # fmt: skip
    scope_file.write_text(json.dumps(scope, indent=1), encoding="utf-8")
    cont = run(*common, "--phase", "continue")
    print(cont.stdout[-600:], cont.stderr[-300:])


if __name__ == "__main__":
    main()

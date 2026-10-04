# ruff: noqa: E501
"""T10 option (c), measured on the credal problem (Increment 4): a thin generic harness and a model-written adapter.

The by-hand harness (`docker/sandbox-credal/harness.py`) was written by reading the parent's code. Here the generic
harness (`generic_harness.py`: loading, validity checks, summaries, the result file) stays and a model writes the
parent-specific adapter from the parent's README and the registered target, with the errors of each failed attempt fed
back. Reported: whether the same baseline gate (rule shadow and the judge) accepts the adapter's baseline, how many
attempts it took, the model cost, the wall time, the adapter's size, and what share of the by-hand harness's lines is
the generic part. The image is the by-hand one (patched solver, pinned numpy and cvxpy): building the image is not part
of what this compares.

Writes data/results/t10_adapter_trial.json and docs/results/t10_adapter.py (the accepted or last adapter).

Usage: uv run python scripts/t10_adapter_trial.py [--max-attempts 5] [--max-usd 0.5]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from vera.backends.generator import OpenRouterGenerator
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.loop import credal, problem, questions, tables
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
REPO_README = ROOT / "data" / "cache" / "credal" / "repo" / "README.md"
TARGET = ROOT / "docs" / "results" / "credal_baseline_target.json"
SYSTEM = "You are a careful research engineer. Reply with one Python code block and nothing else of substance."


def readme_section() -> str:
    text = REPO_README.read_text(encoding="utf-8")
    head = text[text.index("## 0) Setup"): text.index("## 1) Synthetic")]
    body = text[text.index("## 2) California Housing"): text.index("## 3)")]
    return head + "\n" + body


def prompt(target: dict, error: str | None, previous: str | None) -> str:
    p = (
        "Write `adapter.py` for a generic harness. The harness calls\n\n"
        "    def run(data_dir: str, work_dir: str, n_replications: int) -> dict\n\n"
        "and checks what comes back. `run` must reproduce the parent paper's California Housing experiment (Section 5.2, "
        "main tables) by calling the parent's own code, installed in this image (package `credal_dro`, command-line tool "
        "`credaldro`), and return, for each of the methods \"lv\" (the parent's method, LV), \"cvar\", \"wass\", "
        "\"ridge\" and \"erm\", a dict of per-replication lists: \"mae\", \"rmse\", \"p98_abs_error\", \"cvar_abs_error\" "
        "(all in units of 1e4 dollars, so divide the parent's dollar values by 1e4) and \"runtime_s\" (seconds per "
        "replication: the parent's validation, solve and likelihood times added). Each list has exactly "
        "`n_replications` values (the paper's 100). The data file `cal_housing.data` is at "
        "`<data_dir>/CaliforniaHousing/cal_housing.data`; set the environment variable `CALIFORNIA_HOUSING_DATASET_DIR` "
        "to `data_dir` for the parent's code. Write all outputs under `work_dir`. There is no network and the image has "
        "no MOSEK licence (the solver is already replaced by an open one). The parent's README, as given:\n\n"
        f"{readme_section()}\n\n"
        "The paper's experiment is named `lv_california_housing_val` in the parent's tool. The registered target "
        f"(the paper's Table 3, mean and SD over 100 replications, units of 1e4):\n"
        + json.dumps({k: target["reference"][k] for k in ("lv", "cvar", "wass", "ridge", "erm")}) + "\n\n"
        "Reply with the complete `adapter.py` in one Python code block."
    )
    if error:
        p += f"\n\nYour previous attempt failed:\n{error}\n\nPrevious code:\n```python\n{previous}\n```\nFix it."
    return p


def extract_code(reply: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\n(.*?)```", reply, re.DOTALL)
    return blocks[-1].strip() + "\n" if blocks else None


def run_harness(work: Path, seeds: int, timeout_s: int) -> tuple[dict | None, str | None]:
    for stale in ("result.json", "exp", "expdata"):
        target = work / stale
        shutil.rmtree(target, ignore_errors=True) if target.is_dir() else target.unlink(missing_ok=True)
    cmd = ["docker", "run", "--rm", "--cpus", "8", "--memory", "8g", "-v", f"{work}:/work", "-w", "/work",
           credal.IMAGE, "python", "generic_harness.py", "--adapter", "/work/adapter.py", "--seeds", str(seeds),
           "--out", "/work/result.json"]  # fmt: skip
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env={"MSYS_NO_PATHCONV": "1", **__import__("os").environ})
    except subprocess.TimeoutExpired:
        return None, f"the run took more than {timeout_s} seconds"
    out = work / "result.json"
    if not out.exists():
        return None, "the harness wrote no result.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    if data.get("error"):
        listing = ", ".join(sorted(p.name for p in work.iterdir()))
        return None, f"{data['error'][-1200:]}\n(files in work_dir: {listing})"
    cell = data["datasets"]["california_housing"]
    bad = [m for m, c in {"lv": cell, **cell["reference_methods"]}.items() if not c.get("valid")]
    if bad:
        return None, "invalid cells: " + "; ".join(f"{m}: {({'lv': cell, **cell['reference_methods']}[m]).get('invalid_reason')}" for m in bad)
    return data["datasets"], None


def lines(path: Path) -> int:
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-attempts", type=int, default=5)
    ap.add_argument("--max-usd", type=float, default=0.5)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--seeds", type=int, default=100)
    args = ap.parse_args()
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    run_id = "t10-adapter-1"
    ledger = Ledger.for_run(run_id, root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=args.max_usd, max_wall_seconds=4 * 3600)
    gen = OpenRouterGenerator("sonnet", "anthropic/claude-sonnet-5.5", ledger=ledger, budget=budget, max_tokens=8000,
                              reasoning={"effort": "minimal"})  # fmt: skip
    work = ROOT / "runs" / run_id
    (work / "data").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "data" / "raw" / "datasets" / "CaliforniaHousing", work / "data" / "CaliforniaHousing", dirs_exist_ok=True)
    shutil.copy(ROOT / "docker" / "sandbox-credal" / "generic_harness.py", work / "generic_harness.py")
    attempts, error, code, accepted = [], None, None, None
    started = datetime.now(UTC)
    for n in range(1, args.max_attempts + 1):
        reply = gen.generate(SYSTEM, prompt(target, error, code), component="t10.adapter")
        code = extract_code(reply)
        if code is None:
            error, code = "the reply had no Python code block", reply[-1500:]
            attempts.append({"attempt": n, "error": error})
            continue
        (work / "adapter.py").write_text(code, encoding="utf-8")
        t0 = time.time()
        datasets, error = run_harness(work, args.seeds, args.timeout)
        attempts.append({"attempt": n, "seconds": round(time.time() - t0), "error": error, "adapter_lines": lines(work / "adapter.py")})
        if error is None:
            accepted = datasets
            break
    gate = None
    if accepted:
        with problem.using(credal.CREDAL):
            question, material, shadow = questions.baseline_reproduced(target, {tables.BASELINE: accepted}, args.seeds, ["california_housing"])
            (verdict,) = cheap_path(ledger=ledger, budget=budget, component="t10.baseline_gate").ask(material, [question])
        gate = {"rule_shadow": shadow, "judge_answer": verdict.answer, "judge_confidence": verdict.confidence,
                "material": material}  # fmt: skip
    by_hand, generic = lines(ROOT / "docker" / "sandbox-credal" / "harness.py"), lines(ROOT / "docker" / "sandbox-credal" / "generic_harness.py")
    out = {"started": started.strftime("%Y-%m-%dT%H:%M:%SZ"), "attempts": attempts, "accepted": accepted is not None,
           "gate": gate, "model_cost_usd": round(budget.spent_usd, 4), "ledger": ledger.path.relative_to(ROOT).as_posix(),
           "adapter_lines": lines(work / "adapter.py"), "by_hand_harness_lines": by_hand, "generic_harness_lines": generic,
           "generic_share_of_by_hand_pct": round(100 * generic / by_hand, 1),
           "note": "the image is the by-hand one; the generic harness is a separate file written for this comparison"}  # fmt: skip
    (ROOT / "data" / "results" / "t10_adapter_trial.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    shutil.copy(work / "adapter.py", ROOT / "docs" / "results" / "t10_adapter.py")
    print({k: v for k, v in out.items() if k != "gate"}, "gate:", None if gate is None else {k: v for k, v in gate.items() if k != "material"})


if __name__ == "__main__":
    main()

"""The per-stage cost report and the `loop_run` check (tools/checks/check_run.py), on a fake complete run. Offline."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from tests.loop_fakes import make_deps, paper
from vera.loop.graph import run_loop
from vera.loop.report import build_report, write_report

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "checks" / "check_run.py"


def fake_root(tmp_path: Path, run_id: str = "loop-001", draft: str | None = None) -> tuple[Path, dict]:
    """A repo-shaped tree (runs/, data/ledger/, data/results/) holding one finished fake run."""
    build = tmp_path / "build"
    deps = make_deps(build, run_id=run_id)
    if draft is not None:
        deps.generator.drafts = [draft]
    state = run_loop(deps)
    root = tmp_path / "root"
    shutil.copytree(deps.run_dir, root / "runs" / run_id)
    (root / "data" / "ledger").mkdir(parents=True)
    shutil.copy(deps.ledger.path, root / "data" / "ledger" / f"run_{run_id}.jsonl")
    write_report(deps, state, root)
    return root, state


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True)


def test_RSH_P_01_the_report_tabulates_cost_per_stage_and_matches_the_ledger(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    state = run_loop(deps)
    report = build_report(deps, state)
    assert report["completed"] and report["total_cost_usd"] == round(deps.ledger.total_cost(), 6)
    assert (
        sum(c["cost_usd"] for c in report["by_component"].values()) == report["total_cost_usd"]
        or abs(sum(c["cost_usd"] for c in report["by_component"].values()) - report["total_cost_usd"]) < 1e-6
    )
    assert {"p3.ideate", "p3.subset_exp", "p3.write_up", "p2.judge"} <= set(report["by_component"])
    assert [s["stage"] for s in report["stages"]] == ["baseline", "ideate", "subset_exp", "write_up", "audit"]
    assert report["audit"]["overall"] == "green" and "method_code" in report["audit"]["checks_skipped"]
    assert report["best_idea"] == "C1: shared knots" and "TreeHFD (baseline)" in report["held_out_residual_mse_pct"]


def test_RSH_P_01_a_stopped_run_is_reported_as_stopped_not_hidden(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(words=900)]  # the write-up never meets the guidance
    state = run_loop(deps)
    report = build_report(deps, state)
    assert report["completed"] is False and report["stop"]["stage"] == "write_up" and report["audit"] is None


def test_loop_run_check_passes_a_complete_run(tmp_path: Path) -> None:
    root, _ = fake_root(tmp_path)
    out = check(root)
    assert out.returncode == 0, out.stderr
    assert "complete run loop-001" in out.stdout


def test_loop_run_check_blocks_when_there_is_no_run(tmp_path: Path) -> None:
    (tmp_path / "runs").mkdir()
    out = check(tmp_path)
    assert out.returncode == 2 and "no run with the prefix" in out.stderr


def test_loop_run_check_blocks_a_run_that_stopped_before_the_end(tmp_path: Path) -> None:
    root, _ = fake_root(tmp_path, draft=paper(words=900))
    out = check(root)
    assert out.returncode == 2 and "did not finish" in out.stderr


def test_loop_run_check_blocks_a_red_audit_and_names_it(tmp_path: Path) -> None:
    root, _ = fake_root(tmp_path, draft=paper(extra="\nC1 lowered the baseline residual by 41% on Analytical.\n"))
    out = check(root)
    assert out.returncode == 2 and "did not finish" in out.stderr  # the failing audit stopped the run


def test_loop_run_check_blocks_spend_that_is_not_in_the_ledger(tmp_path: Path) -> None:
    root, _ = fake_root(tmp_path)
    ledger = root / "data" / "ledger" / "run_loop-001.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    ledger.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")  # a call went missing from the ledger
    out = check(root)
    assert out.returncode == 2 and "differs from the ledger" in out.stderr


def test_loop_run_check_blocks_a_missing_cost_report_and_lists_every_failed_attempt(tmp_path: Path) -> None:
    root, _ = fake_root(tmp_path)
    (root / "data" / "results" / "run_loop-001.json").unlink()
    second = root / "runs" / "loop-002"
    second.mkdir()
    out = check(root)
    assert out.returncode == 2
    assert "loop-001" in out.stderr and "loop-002" in out.stderr and "cost table" in out.stderr
    report = json.loads((root / "runs" / "loop-001" / "best_so_far.json").read_text(encoding="utf-8"))
    assert report["stop_reason"] == "completed"

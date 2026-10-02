"""The trusted experiment harness (docker/sandbox-treehfd/harness.py), run in the real sandbox. Needs Docker.

Skipped when Docker, the image or the Airfoil dataset (scripts/fetch_datasets.py) is missing, unless
VERA_REQUIRE_DOCKER=1, which the `sandbox_ready` gate sets.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from vera.sandbox import SandboxLimits, SandboxUnavailable, check_available, run_script

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "docker" / "sandbox-treehfd" / "harness.py"
AIRFOIL = ROOT / "data" / "raw" / "datasets" / "airfoil_self_noise.dat"

try:
    check_available()
    WHY = "" if AIRFOIL.exists() else "Airfoil dataset not fetched (scripts/fetch_datasets.py)"
except SandboxUnavailable as exc:
    WHY = str(exc)

needs_harness = pytest.mark.skipif(bool(WHY), reason=WHY)


def run_harness(tmp_path: Path, method: str | None, seeds: int = 1) -> dict:
    """Run the harness on Airfoil with `method` source (None = the parent's baseline); returns its result.json."""
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy(HARNESS, tmp_path / "harness.py")
    shutil.copy(AIRFOIL, tmp_path / "data" / AIRFOIL.name)
    target = "baseline"
    if method is not None:
        (tmp_path / "method.py").write_text(method, encoding="utf-8")
        target = "/work/method.py"
    driver = (
        "import sys\nsys.path.insert(0, '/work')\nimport harness\n"
        f"harness.main(['--method', {target!r}, '--datasets', 'airfoil', '--seeds', '{seeds}'])\n"
    )
    res = run_script(driver, tmp_path, limits=SandboxLimits(wall_seconds=300, memory_mb=2048))
    assert res.exit_code == 0, res.stderr[-800:]
    return json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))


CONSTANT = (
    "import numpy as np\n\n\ndef decompose(model, X_train, X_test):\n"
    "    return float(np.mean(model.predict(X_train))), {(0,): np.zeros(len(X_test))}\n"
)
CHEAT = "def decompose(model, X_train, X_test):\n    return 0.0, {(0,): model.predict(X_test)}\n"


@needs_harness
def test_RSH_F_02_harness_reports_the_held_out_and_the_in_sample_residual(tmp_path: Path) -> None:
    out = run_harness(tmp_path, CONSTANT)
    air = out["datasets"]["airfoil"]
    assert air["valid"] and "error" not in out
    # a constant decomposition explains none of the model's variance, on either row set
    for key in ("residual_mse_pct", "residual_in_sample_pct"):
        assert 60 < air[key]["mean"] < 140, air[key]
    assert air["runtime_s"]["mean"] > 0 and air["n_seeds"] == 1


@needs_harness
def test_RSH_F_02_harness_rejects_a_component_that_depends_on_other_variables(tmp_path: Path) -> None:
    out = run_harness(tmp_path, CHEAT)  # returning the model's own predictions as a "main effect" would score 0%
    air = out["datasets"]["airfoil"]
    assert air["valid"] is False and "depends on variables outside (0,)" in air["invalid_reason"]
    assert "residual_mse_pct" not in air  # no number is reported for an invalid method


@needs_harness
def test_RSH_F_02_harness_reports_a_method_error_instead_of_crashing(tmp_path: Path) -> None:
    out = run_harness(tmp_path, "def decompose(model, X_train, X_test):\n    raise ValueError('nope')\n")
    assert "ValueError: nope" in out["error"]


@needs_harness
def test_RSH_F_02_the_baseline_is_deterministic_and_reproduces_the_papers_airfoil_value_in_sample(
    tmp_path: Path,
) -> None:
    first = run_harness(tmp_path / "a", None)["datasets"]["airfoil"]
    second = run_harness(tmp_path / "b", None)["datasets"]["airfoil"]
    assert first["valid"] and second["valid"]
    for key in ("residual_mse_pct", "residual_in_sample_pct"):  # treehfd's unseeded tie-break is fixed by the harness
        assert first[key]["values"] == second[key]["values"]
    # docs/results/treehfd_baseline_target.json: in-sample reproduces the paper's 2.0 within 1.0 point;
    # held-out is much higher (the first runs: 4.8 vs 1.7 on seed 0)
    assert abs(first["residual_in_sample_pct"]["mean"] - 2.0) <= 1.0
    assert first["residual_mse_pct"]["mean"] > 3.0

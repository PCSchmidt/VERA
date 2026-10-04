"""The protocol stage with a fake sandbox: no Docker, no network, no model calls."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from tests.loop_fakes import make_deps
from vera.loop import protocol_stage, tables
from vera.sandbox import SandboxResult
from vera.schemas import ProtocolSpec

DATASETS = ["analytical@0", "analytical@0.5", "airfoil"]


def cell(value: float, *, valid: bool = True) -> dict:
    if not valid:
        return {"valid": False, "invalid_reason": "component (1, 2) depends on variables outside (1, 2)"}
    m = {"mean": value, "std": 0.1, "values": [value]}
    return {"valid": True, "invalid_reason": None, "n_seeds": 3, "n_boot": 5, "own_variables_only": True,
            "component_mse_pct": m, "component_mse": m, "residual_mse_pct": m, "rank_stability": m,
            "rank_vs_truth": m, "runtime_s": m}  # fmt: skip


class FakeProtocolSandbox:
    """Writes the harness's protocol result.json for the dataset and methods in the driver."""

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    def __call__(self, source: str, workdir: Path, *, limits=None, budget=None, **_):
        dataset = re.search(r"'--protocol-datasets', '([^']+)'", source).group(1)
        methods = re.search(r"'--method', '([^']+)'", source).group(1).split(",")
        self.calls.append(dataset)
        if self.fail:
            return SandboxResult(1, "", "boom", False, False, 1.0, 0.0, False, False, None, "fake")
        results = {m: {dataset: cell(1.0 + i, valid=not (m == "treeshap" and dataset == "airfoil"))}
                   for i, m in enumerate(methods)}  # fmt: skip
        (workdir / "result.json").write_text(json.dumps({"protocol": True, "results": results}), encoding="utf-8")
        return SandboxResult(0, "ok", "", False, False, 1.0, 0.0, False, False, None, "fake")


def register(tmp_path: Path) -> dict:
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"datasets": DATASETS, "n_boot": 5}), encoding="utf-8")
    spec = ProtocolSpec(id="p", question="q?", methods=["treehfd", "treeshap"], datasets=DATASETS,
                        metrics=["component_mse_pct"], primary_metric="component_mse_pct", n_seeds=3,
                        target_file="target.json",
                        target_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    return {"spec": spec, "root": tmp_path}


def state_with_idea(deps) -> dict:
    code = "def decompose(model, X_train, X_test):\n    return 0.0, {}\n"
    raw = {"log": {"Idea A": {"ok": True, "attempts": [{"attempt": 1, "error": None, "code": code}]},
                   "Idea B": {"ok": False, "attempts": [{"attempt": 1, "error": "x"}]}}}  # fmt: skip
    path = deps.run_dir / "artifacts" / "subset_exp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw), encoding="utf-8")
    return {"artifacts": {"subset_exp_raw": "artifacts/subset_exp.json"}}


def test_a_run_without_a_registered_protocol_skips_the_stage(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    assert protocol_stage.protocol_node(deps)({}) == {}


def test_the_stage_runs_every_dataset_for_the_reference_methods_and_valid_ideas(tmp_path: Path) -> None:
    sandbox = FakeProtocolSandbox()
    deps = make_deps(tmp_path, sandbox=sandbox)
    deps.extra["protocol"] = register(tmp_path)
    update = protocol_stage.protocol_node(deps)(state_with_idea(deps))
    assert sorted(sandbox.calls) == sorted(DATASETS)
    protocol = update["protocol"]
    assert protocol["methods"] == ["TreeHFD", "TreeSHAP", "Idea A"]  # Idea B had no valid run
    assert set(protocol["results"]["TreeHFD"]) == set(DATASETS)
    assert protocol["results"]["TreeSHAP"]["airfoil"]["valid"] is False  # recorded with its reason, not filled in
    assert (deps.run_dir / "artifacts" / "protocol.json").exists()


def test_a_protocol_changed_after_registration_is_not_run(tmp_path: Path) -> None:
    sandbox = FakeProtocolSandbox()
    deps = make_deps(tmp_path, sandbox=sandbox)
    deps.extra["protocol"] = register(tmp_path)
    (tmp_path / "target.json").write_text(json.dumps({"datasets": ["analytical@0"], "n_boot": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="changed after it was registered"):
        protocol_stage.protocol_node(deps)(state_with_idea(deps))
    assert sandbox.calls == []


def test_a_failed_sandbox_stops_the_run_with_the_reason(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, sandbox=FakeProtocolSandbox(fail=True))
    deps.extra["protocol"] = register(tmp_path)
    update = protocol_stage.protocol_node(deps)(state_with_idea(deps))
    assert update["stop"]["reason"].startswith("protocol: the protocol run for")


def test_the_rendered_tables_mark_invalid_and_inapplicable_cells(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, sandbox=FakeProtocolSandbox())
    deps.extra["protocol"] = register(tmp_path)
    protocol = protocol_stage.protocol_node(deps)(state_with_idea(deps))["protocol"]
    protocol["results"]["TreeHFD"]["airfoil"]["component_mse_pct"] = None  # no true components on Airfoil
    text = tables.render_protocol(protocol)
    assert "Component error against the true decomposition" in text and "Analytical, rho 0.5" in text
    assert "| TreeSHAP |" in text and "invalid" in text and "Invalid cells:" in text
    assert "n/a" in text

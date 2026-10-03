"""Extension datasets (docs/results/treehfd_baseline_target.json, 2026-10-03): the analytical case at other rho.

They have no paper reference. The baseline-reproduction gate checks only the registered datasets against the paper, and
requires the baseline's result on an extension dataset to be valid; the ideas stage and the write-up are told what the
extension datasets are.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.loop_fakes import BASELINE_OK, TARGET, FakeSandbox, ds, make_deps, make_spec
from vera.loop import questions, stages, tables, writeup
from vera.loop.graph import run_loop

HARNESS = Path(__file__).resolve().parents[1] / "docker" / "sandbox-treehfd" / "harness.py"
EXT = ["uncorrelated", "correlated95"]


def spec_with(datasets: list[str]):
    spec = make_spec()
    return spec.model_copy(update={"problem": spec.problem.model_copy(update={"datasets": datasets})})


def test_the_extension_datasets_are_registered_with_no_reference() -> None:
    assert set(TARGET["extension_datasets"]) == set(EXT)
    assert not set(EXT) & set(TARGET["datasets"])  # the reproduced datasets, and what audit code reads, are unchanged
    assert all(v["reference_pct"] is None for v in TARGET["extension_datasets"].values())
    assert TARGET["changes"][-1]["date"] == "2026-10-03" and TARGET["changes"][-1]["decided_by"] == "Chris"


def test_the_harness_defines_the_correlated_variants_of_the_analytical_case() -> None:
    tree = ast.parse(HARNESS.read_text(encoding="utf-8"))
    source = HARNESS.read_text(encoding="utf-8")
    assert "rho: float = 0.5" in source  # the registered dataset keeps the paper's correlation
    assert '"uncorrelated"' in source and "rho=0.0" in source
    assert '"correlated95"' in source and "rho=0.95" in source
    assert any(isinstance(n, ast.FunctionDef) and n.name == "analytical" for n in ast.walk(tree))


def test_the_reproduction_question_ignores_extension_datasets() -> None:
    results = {tables.BASELINE: BASELINE_OK | {"correlated95": ds(9.0, in_sample=9.0)}}
    question, material, shadow = questions.baseline_reproduced(TARGET, results, 3, ["analytical", "airfoil", *EXT[1:]])
    assert shadow is True and "Correlated95" not in material  # a wild extension value cannot fail the paper comparison


def test_a_valid_baseline_on_the_extension_datasets_passes_the_gate(tmp_path: Path) -> None:
    baseline = BASELINE_OK | {d: ds(3.0, in_sample=1.0) for d in EXT}
    deps = make_deps(tmp_path, spec=spec_with(["analytical", "airfoil", *EXT]), sandbox=FakeSandbox(baseline=baseline))
    state = run_loop(deps)
    assert "baseline_gate" in state["trail"] and not (state.get("stop") or {}).get("stage") == "baseline"


def test_an_invalid_baseline_on_an_extension_dataset_stops_the_run(tmp_path: Path) -> None:
    baseline = BASELINE_OK | {"uncorrelated": ds(3.0), "correlated95": ds(0, valid=False, reason="failed")}
    deps = make_deps(tmp_path, spec=spec_with(["analytical", "airfoil", *EXT]), sandbox=FakeSandbox(baseline=baseline))
    state = run_loop(deps)
    assert state["stop"]["stage"] == "baseline" and "correlated95" in state["stop"]["reason"]
    assert deps.generator.calls == []  # no idea was generated


def test_the_ideas_prompt_and_the_write_up_facts_name_the_extension_datasets(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, spec=spec_with(["analytical", "airfoil", *EXT]))
    assert "pairwise correlation 0.95" in stages.ideate_prompt(deps, "table", 3)
    results = {tables.BASELINE: BASELINE_OK | {d: ds(3.0, in_sample=1.0) for d in EXT}}
    state = {"results": results, "ideas": [], "best": None, "verdicts": {"baseline": {"answer": True}}}
    assert "Dataset Correlated95: The analytical dataset with pairwise correlation 0.95" in writeup.facts(
        state, deps
    )
    (tmp_path / "plain").mkdir()
    plain = make_deps(tmp_path / "plain", spec=make_spec())
    assert "Dataset " not in stages.ideate_prompt(plain, "table", 3)  # a run without them is unchanged

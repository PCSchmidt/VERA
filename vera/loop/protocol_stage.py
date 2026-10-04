"""The protocol stage (Increment 4): run the registered experiment the confirmed question describes.

After the idea gate and before the write-up, when the run carries a registered protocol (`deps.extra["protocol"]`:
`spec` a `ProtocolSpec`, `root` the repository root), this stage

1. checks the protocol's target file still has the hash the spec registered (a protocol changed after registration is
   not run);
2. runs the harness's protocol mode (`docker/sandbox-treehfd/protocol.py`) once per registered dataset, in parallel
   sandboxes: the reference methods (TreeHFD, TreeSHAP) and every idea that had a valid subset run, on the same cells;
3. keeps the harness's cells as they came back: a cell the harness could not compute is recorded with its reason,
   never filled in; the table and the write-up report it as invalid.

The numbers are VERA's (the harness's), never a model's. The stage spends no model calls. It writes
`artifacts/protocol.json` and puts `protocol` in the state for the write-up and `results.json`.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vera.loop.stages import LoopDeps, _prepare_workdir, _stop, _write_json
from vera.sandbox import SandboxLimits

PROTOCOL_LIMITS = SandboxLimits(wall_seconds=3600, memory_mb=3072, cpus=2.0, pids=256)
STAGE = "subset_exp"  # the experiment stage; `protocol` is not a stage of its own in the schema
REFERENCE = {"treehfd": "TreeHFD", "treeshap": "TreeSHAP"}


def registered(deps: LoopDeps) -> tuple[dict, dict] | None:
    """(spec JSON, target JSON) of the run's protocol after the hash check, or None when the run has none."""
    held = deps.extra.get("protocol")
    if held is None:
        return None
    spec = held["spec"]
    target_path = Path(held["root"]) / spec.target_file
    if hashlib.sha256(target_path.read_bytes()).hexdigest() != spec.target_sha256:
        raise ValueError(f"{spec.target_file} changed after it was registered: the protocol is not run")
    return spec.model_dump(mode="json"), json.loads(target_path.read_text(encoding="utf-8"))


def idea_sources(state: dict, deps: LoopDeps) -> dict[str, str]:
    """idea name -> the code of its valid run (the last attempt that passed), from the subset-experiment artifact."""
    raw = json.loads((deps.run_dir / state["artifacts"]["subset_exp_raw"]).read_text(encoding="utf-8"))
    out = {}
    for name, entry in raw["log"].items():
        good = [a for a in entry["attempts"] if a.get("error") is None and a.get("code")]
        if entry["ok"] and good:
            out[name] = good[-1]["code"]
    return out


def run_dataset(deps: LoopDeps, dataset: str, index: int, ideas: dict[str, str], seeds: int, boot: int) -> dict:
    """The harness's protocol cells for one dataset: {method label: cell}. Raises if the sandbox run failed."""
    wd = _prepare_workdir(deps, f"protocol_{index}")
    paths = {}
    for k, (name, code) in enumerate(ideas.items(), start=1):
        (wd / f"method_{k}.py").write_text(code, encoding="utf-8")
        paths[f"/work/method_{k}.py"] = name
    methods = ",".join([*REFERENCE, *paths])
    driver = (
        "import sys\nsys.path.insert(0, '/work')\nimport harness\n"
        f"harness.main(['--protocol', '--method', {methods!r}, '--protocol-datasets', {dataset!r}, "
        f"'--seeds', '{seeds}', '--boot', '{boot}'])\n"
    )
    res = deps.sandbox(driver, wd, limits=PROTOCOL_LIMITS, budget=None)  # the stage charges its wall time once
    if res.timed_out or res.oom_killed or res.workdir_over_limit:
        why = "timed out" if res.timed_out else "ran out of memory" if res.oom_killed else "wrote too much"
        raise RuntimeError(f"the protocol run for {dataset} {why}")
    out_file = wd / "result.json"
    if res.exit_code != 0 or not out_file.exists():
        raise RuntimeError(f"the protocol run for {dataset} failed (exit {res.exit_code}): {res.stderr[-500:]}")
    results = json.loads(out_file.read_text(encoding="utf-8"))["results"]
    labels = {**REFERENCE, **paths}
    return {labels[m]: cells[dataset] for m, cells in results.items()}


def protocol_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        reg = registered(deps)
        if reg is None:
            return {}  # a run without a registered protocol skips this stage without a trace
        spec, target = reg
        ideas = idea_sources(state, deps)
        datasets = list(spec["datasets"])
        started = time.monotonic()
        try:
            with ThreadPoolExecutor(min(len(datasets), 8)) as pool:
                parts = list(
                    pool.map(
                        lambda a: run_dataset(deps, a[1], a[0], ideas, spec["n_seeds"], target["n_boot"]),
                        enumerate(datasets),
                    )
                )
        except RuntimeError as exc:
            return _stop(STAGE, f"protocol: {exc}")
        finally:  # the datasets ran side by side: the run's clock advances by the elapsed time, not their sum
            deps.budget.charge(0.0, seconds=int(time.monotonic() - started), calls=0)
        methods = [*REFERENCE.values(), *ideas]
        results = {m: {ds: part[m] for ds, part in zip(datasets, parts, strict=True)} for m in methods}
        protocol = {"protocol_id": spec["id"], "target_sha256": spec["target_sha256"], "datasets": datasets,
                    "methods": methods, "metrics": list(spec["metrics"]), "n_seeds": spec["n_seeds"],
                    "n_boot": target["n_boot"], "results": results}  # fmt: skip
        artifact = _write_json(deps, "protocol", protocol)
        return {"protocol": protocol, "artifacts": {"protocol_raw": artifact}, "trail": ["protocol"]}

    return node

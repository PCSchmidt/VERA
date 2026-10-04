# ruff: noqa: E501
"""Run the registered tree-explain protocol in the sandbox image, one container per dataset, in parallel.

Checks first that the target file still has the hash the ProtocolSpec registered. Each dataset cell (analytical at one
correlation, or Airfoil) runs in its own container (`harness.py --protocol`), the cells are merged into
data/results/protocol_<tag>.json with the registration's hash and the image tag. No model calls: compute only.

Usage: uv run python scripts/run_protocol.py --tag tree-explain-1 [--methods treehfd,treeshap] [--workers 3]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "vera-sandbox-treehfd:dd02152"
HARNESS_DIR = ROOT / "docker" / "sandbox-treehfd"


def run_cell(dataset: str, methods: str, seeds: int, boot: int, data_dir: Path) -> dict:
    with tempfile.TemporaryDirectory(dir=ROOT / "runs") as tmp:
        wd = Path(tmp)
        for f in ("harness.py", "protocol.py", "truth.py"):
            shutil.copy(HARNESS_DIR / f, wd / f)
        (wd / "data").mkdir()
        for f in data_dir.glob("*"):
            if f.is_file():
                shutil.copy(f, wd / "data" / f.name)
        cmd = ["docker", "run", "--rm", "--cpus", "2", "-v", f"{wd}:/work", "-w", "/work", IMAGE, "python", "harness.py",
               "--protocol", "--method", methods, "--protocol-datasets", dataset, "--seeds", str(seeds),
               "--boot", str(boot), "--out", "/work/r.json"]  # fmt: skip
        proc = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        out = wd / "r.json"
        if proc.returncode or not out.exists():
            raise SystemExit(f"{dataset}: the container failed: {proc.stderr[-600:]}")
        return json.loads(out.read_text(encoding="utf-8"))["results"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--methods", default="treehfd,treeshap")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", help="comma list of the registered datasets to run (a re-run after a harness bug fix)")
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw" / "datasets"))
    args = ap.parse_args()
    spec = json.loads((ROOT / "docs" / "results" / "tree_explain_protocol_spec.json").read_text(encoding="utf-8"))
    target = ROOT / spec["target_file"]
    if hashlib.sha256(target.read_bytes()).hexdigest() != spec["target_sha256"]:
        raise SystemExit("the protocol target file changed after registration: refusing to run")
    registered = json.loads(target.read_text(encoding="utf-8"))
    datasets, seeds, boot = registered["datasets"], registered["n_seeds"], registered["n_boot"]
    if args.only:
        datasets = [d for d in datasets if d in args.only.split(",")]
    out_path = ROOT / "data" / "results" / f"protocol_{args.tag}.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.name} exists: results are never overwritten")
    (ROOT / "runs").mkdir(exist_ok=True)
    with ThreadPoolExecutor(args.workers) as pool:
        parts = list(pool.map(lambda d: run_cell(d, args.methods, seeds, boot, Path(args.data_dir)), datasets))
    merged: dict = {m: {} for m in args.methods.split(",")}
    for part in parts:
        for m, cells in part.items():
            merged[m].update(cells)
    out_path.write_text(json.dumps({"protocol_id": spec["id"], "target_sha256": spec["target_sha256"], "image": IMAGE,
                                    "seeds": seeds, "boot": boot, "results": merged}, indent=1), encoding="utf-8")  # fmt: skip
    print(f"wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

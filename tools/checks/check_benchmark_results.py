"""The benchmark run is complete, on the fixed test split, inside its budget (gate benchmark_run; JDG-F-06).

Blocks unless:
- data/benchmark/results.json names a reference backend and has metrics for
  at least two backends, each with every metric JDG-F-06 asks for;
- every non-reference backend has a threshold sweep covering 0.00-1.00 in
  steps of 0.05, each row with agreement, cost, latency and escalation rate;
- the test split is unchanged since labelling: the hash recomputed from
  data/benchmark/items.jsonl equals split.json's and results.json's;
- the run's ledgers (data/ledger/bench_*.jsonl), summed here, total no more
  than $8.00.
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg

MAX_USD = 8.00
BACKEND_KEYS = ["agreement_label", "agreement_reference", "ece", "flip_rate", "cost_per_item_usd", "latency_p50_ms",
                "latency_p95_ms", "malformed_rate", "items", "repeats"]  # fmt: skip
SWEEP_KEYS = ["threshold", "agreement_label", "agreement_reference", "escalation_rate", "cost_per_item_usd",
              "latency_p50_ms", "latency_p95_ms"]  # fmt: skip
THRESHOLDS = [round(0.05 * k, 2) for k in range(21)]


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    bench = root / "data" / "benchmark"
    for rel in ("results.json", "split.json", "items.jsonl"):
        if not (bench / rel).exists():
            block(f"data/benchmark/{rel} not found")
    results = json.loads((bench / "results.json").read_text(encoding="utf-8"))
    backends, sweeps, ref = results.get("backends") or {}, results.get("sweep") or {}, results.get("reference")

    if len(backends) < 2:
        block(f"metrics for {len(backends)} backend(s); need at least 2")
    if ref not in backends:
        block(f"reference backend {ref!r} has no metrics")
    for name, m in backends.items():
        missing = [k for k in BACKEND_KEYS if m.get(k) is None]
        if missing:
            block(f"backend {name}: missing metrics {missing}")
    for name in backends:
        if name == ref:
            continue
        rows = sweeps.get(name) or []
        if sorted(r.get("threshold") for r in rows) != THRESHOLDS:
            block(f"backend {name}: sweep does not cover thresholds 0.00-1.00 in 0.05 steps")
        for r in rows:
            missing = [k for k in SWEEP_KEYS if r.get(k) is None]
            if missing:
                block(f"backend {name}, threshold {r.get('threshold')}: missing {missing}")

    lines = [ln for ln in (bench / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    test = sorted((json.loads(ln)["id"], ln) for ln in lines if json.loads(ln).get("split") == "test")
    digest = hashlib.sha256("\n".join(ln for _, ln in test).encode("utf-8")).hexdigest()
    recorded = json.loads((bench / "split.json").read_text(encoding="utf-8")).get("test_sha256")
    if digest != recorded:
        block(f"test split changed since labelling: {digest[:12]}… != split.json {str(recorded)[:12]}…")
    if results.get("test_sha256") != digest:
        block("results.json was computed on a different test split")

    ledgers = sorted((root / "data" / "ledger").glob("bench_*.jsonl"))
    if not ledgers:
        block("no run ledgers (data/ledger/bench_*.jsonl)")
    total = 0.0
    for path in ledgers:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += float(json.loads(line)["cost_usd"])
    if total > MAX_USD:
        block(f"run ledgers total ${total:.4f} > ${MAX_USD:.2f}")

    ok(
        f"{len(backends)} backends (reference {ref}), {len(sweeps)} sweeps x {len(THRESHOLDS)} thresholds; "
        f"test hash {digest[:12]}… unchanged; run ledgers ${total:.4f} <= ${MAX_USD:.2f}"
    )


if __name__ == "__main__":
    main()

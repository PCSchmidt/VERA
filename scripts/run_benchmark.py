"""Increment 1 benchmark run and report (JDG-F-06; gate benchmark_run). Test split only.

  run     every candidate backend (vera/bench/candidates.py) on the test split:
          cheap backends 10 repeats, the reference 3. Backends run in parallel
          threads, each with its own ledger (data/ledger/bench_<name>.jsonl)
          and its own slice of the $8.00 budget (slices sum to <= $8.00).
          Verdicts go to data/benchmark/raw/<name>.jsonl; a rerun resumes.
  report  metrics per backend, the offline threshold sweep of each cheap
          backend against the reference, and the run's ledger total ->
          data/benchmark/results.json and docs/figures/threshold_curve.png.

Both refuse to start unless the test split still matches the SHA-256
recorded in data/benchmark/split.json before any result was seen (docs/06 §5).

Usage: uv run --group bench python scripts/run_benchmark.py run [--backends ...]
       uv run --group bench python scripts/run_benchmark.py report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.bench.candidates import LOCAL, NAMES, REFERENCE, make_backend  # noqa: E402
from vera.bench.harness import load_recs, run_backend  # noqa: E402
from vera.bench.metrics import backend_metrics, modal_answers, sweep  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.schemas import BenchmarkItem, Budget  # noqa: E402

BENCH = ROOT / "data" / "benchmark"
RAW = BENCH / "raw"
LEDGERS = ROOT / "data" / "ledger"
FIGURE = ROOT / "docs" / "figures" / "threshold_curve.png"
MAX_USD = 8.00
SLICE_USD = {REFERENCE: 5.00}  # every other backend: DEFAULT_SLICE
DEFAULT_SLICE = 0.50
REPEATS = {REFERENCE: 3}  # every other backend: 10
DEFAULT_REPEATS = 10
DEFAULT_THRESHOLD = 0.7  # RoutingPolicy default, reported as the operating point


def test_items() -> tuple[list[BenchmarkItem], str]:
    lines = [ln for ln in (BENCH / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    items = [BenchmarkItem.model_validate_json(ln) for ln in lines]
    test = sorted(((i.id, ln) for i, ln in zip(items, lines, strict=True) if i.split == "test"))
    digest = hashlib.sha256("\n".join(ln for _, ln in test).encode("utf-8")).hexdigest()
    recorded = json.loads((BENCH / "split.json").read_text(encoding="utf-8"))["test_sha256"]
    if digest != recorded:
        sys.exit(f"refusing: test split hash {digest[:12]}… != split.json {recorded[:12]}…")
    return [i for i in items if i.split == "test"], digest


def cmd_run(names: list[str]) -> None:
    items, _ = test_items()
    slices = {n: SLICE_USD.get(n, DEFAULT_SLICE) for n in NAMES}
    assert sum(slices.values()) <= MAX_USD, "budget slices exceed the run's $8.00"
    backends = []
    for name in names:  # constructed here: OpenRouter backends fetch catalogue prices
        ledger = Ledger(LEDGERS / f"bench_{name}.jsonl", run_id="bench")
        budget = Budget(max_usd=slices[name], max_wall_seconds=6 * 3600)
        budget.charge(ledger.total_cost(), calls=0)  # a resumed run keeps what it already spent
        backends.append((make_backend(name, ledger=ledger, budget=budget, component="p2.bench"), budget))
    errors: list[str] = []

    def work(backend, budget) -> None:
        try:
            n = run_backend(backend, items, REPEATS.get(backend.name, DEFAULT_REPEATS), RAW / f"{backend.name}.jsonl",
                            progress=lambda m: print(m, flush=True))  # fmt: skip
            print(f"{backend.name}: {n} new verdicts, ${budget.spent_usd:.4f} spent", flush=True)
        except Exception as err:  # noqa: BLE001 - reported; other backends continue
            errors.append(f"{backend.name}: {type(err).__name__}: {err}")

    threads = [threading.Thread(target=work, args=b) for b in backends]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for e in errors:
        print("FAILED", e)
    if errors:
        sys.exit(1)


def cmd_report() -> None:
    _, digest = test_items()
    recs = {f.stem: load_recs(f) for f in sorted(RAW.glob("*.jsonl"))}
    if REFERENCE not in recs:
        sys.exit("no reference verdicts yet")
    ref_modes = modal_answers(recs[REFERENCE])
    backends = {name: backend_metrics(rs, ref_modes) for name, rs in recs.items()}
    sweeps = {name: sweep(rs, recs[REFERENCE]) for name, rs in recs.items() if name != REFERENCE}
    ledger_total = sum(Ledger(p).total_cost() for p in LEDGERS.glob("bench_*.jsonl"))
    results = {
        "built": date.today().isoformat(),
        "test_sha256": digest,
        "reference": REFERENCE,
        "local_backends": sorted(LOCAL),
        "default_threshold": DEFAULT_THRESHOLD,
        "ledger_total_usd": ledger_total,
        "budget_usd": MAX_USD,
        "backends": backends,
        "sweep": sweeps,
        "definitions": "vera/bench/metrics.py (module docstring)",
    }
    (BENCH / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    plot(results)
    print(f"ledger total ${ledger_total:.4f}; wrote {BENCH / 'results.json'} and {FIGURE}")


# ── figure (dataviz skill: categorical slots in fixed order, validated adjacent/light) ──────────────

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # slots 1-5; colour follows the backend
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COST_FLOOR = 1e-6  # a $0 (local) cost is drawn at this floor on the log axis


def plot(results: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cheap = [n for n in NAMES if n in results["sweep"]]  # fixed order from candidates.NAMES
    ref = results["backends"][results["reference"]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True, facecolor=SURFACE)
    panels = [("agreement_label", "Agreement with labels"), ("agreement_reference", "Agreement with reference judge")]
    for ax, (key, title) in zip(axes, panels, strict=True):
        ax.set_facecolor(SURFACE)
        for k, name in enumerate(cheap):
            rows = results["sweep"][name]
            xs = [max(r["cost_per_item_usd"], COST_FLOOR) for r in rows]
            ys = [r[key] for r in rows]
            ax.plot(xs, ys, color=SERIES[k % len(SERIES)], linewidth=2, marker="o", markersize=4, label=name,
                    solid_capstyle="round")  # fmt: skip
            d = next(r for r in rows if r["threshold"] == results["default_threshold"])
            ax.plot([max(d["cost_per_item_usd"], COST_FLOOR)], [d[key]], marker="o", markersize=8,
                    markerfacecolor=SURFACE, markeredgecolor=SERIES[k % len(SERIES)], markeredgewidth=2)  # fmt: skip
            # label each line at its cheap-only end (threshold 0): at threshold 1 every line meets the reference
            ax.annotate(name, (xs[0], ys[0]), xytext=(6, -10), textcoords="offset points", fontsize=8, color=INK_2,
                        ha="left")  # fmt: skip
        ref_y = ref[key]  # for the reference itself, agreement_reference = agreement with its own modal answers
        ax.plot([ref["cost_per_item_usd"]], [ref_y], marker="D", markersize=8, color=INK)
        ax.annotate("Sonnet 5.5 alone", (ref["cost_per_item_usd"], ref_y), xytext=(0, -16), textcoords="offset points",
                    fontsize=8, color=INK, ha="center")  # fmt: skip
        ax.set_xscale("log")
        ax.set_title(title, color=INK, fontsize=11, loc="left")
        ax.set_xlabel("Mean cost per item (USD, log scale)", color=INK_2, fontsize=9)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.tick_params(colors=INK_2, labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
    axes[0].set_ylabel("Share of verdicts", color=INK_2, fontsize=9)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK_2)
    fig.suptitle(
        "Cost vs agreement as the escalation threshold rises from 0 to 1 (left to right on each line); "
        f"open circle = threshold {results['default_threshold']}",
        color=INK,
        fontsize=10,
        x=0.01,
        ha="left",
    )
    fig.text(0.01, 0.005, f"Test split: {ref['items']} items. \\$0 (local) costs drawn at \\${COST_FLOOR:g}. "
             "Sonnet alone on the right: agreement of its repeats with its own modal answer.",
             color=INK_2, fontsize=7)  # fmt: skip
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--backends", nargs="+", default=NAMES, choices=NAMES)
    sub.add_parser("report")
    args = parser.parse_args()
    cmd_run(args.backends) if args.cmd == "run" else cmd_report()


if __name__ == "__main__":
    main()

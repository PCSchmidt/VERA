"""Run (or resume) the research loop on TreeHFD: baseline, ideas, subset experiments, write-up, audit (Increment 2).

One run = one directory `runs/<run_id>/` (git-ignored) with the checkpoints, artifacts, gates.jsonl, paper.md,
audit.md and best_so_far.json, and one never-overwritten ledger `data/ledger/run_<run_id>.jsonl`. A run may take
longer than the agent's 10-minute background limit, so it is resumable: run it from your own terminal, or re-run with
--resume after an interruption (completed nodes and their model calls are not repeated; a node that was interrupted
reruns whole).

Generators (docs/04 T9): `--arm` picks which model writes which stage (ideas, experiment code, write-up), or
`--generator` uses one model for all. `--from-run smoke-007` starts at the ideas stage from that run's recorded
baseline (the same baseline for every arm of the generator comparison; the baseline is not re-run).

Needs Docker running with the sandbox image (docker/sandbox-treehfd/Dockerfile), OPENROUTER_API_KEY and
TYPESAFE_AI_API_KEY in .env, and the datasets (scripts/fetch_datasets.py; `analytical` needs none).

Usage:
  uv run python scripts/run_loop.py --run-id smoke-008 --datasets analytical,airfoil --seeds 3 --max-usd 0.5
  uv run python scripts/run_loop.py --run-id gen-sonnet-1 --arm sonnet --from-run smoke-007 --max-usd 1.5
  uv run python scripts/run_loop.py --run-id smoke-008 ... --resume
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from vera.backends.generator import OpenRouterGenerator
from vera.graph import run_config, sqlite_checkpointer
from vera.judge.cheap_path import cheap_path
from vera.keepawake import keep_awake
from vera.ledger import Ledger
from vera.loop import literature_context, references
from vera.loop.generators import ByStage
from vera.loop.graph import run_loop
from vera.loop.report import write_report
from vera.loop.stages import LoopDeps
from vera.sandbox import check_available, run_script
from vera.schemas import Budget, OutputGuidance, ProblemSpec, ProtocolSpec, RunSpec

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "results" / "treehfd_baseline_target.json"
GENERATORS = {
    "glm-flash": "z-ai/glm-5.3-flash",
    "sonnet": "anthropic/claude-sonnet-5.5",
    "mimo-pro": "xiaomi/mimo-v2.6-pro",
    "deepseek-flash": "deepseek/deepseek-v4.1-flash",
}
STAGES = ("ideate", "subset_exp", "write_up")
ARMS = {  # arm -> generator per stage
    "glm": dict.fromkeys(STAGES, "glm-flash"),
    "glm-sonnet": {"ideate": "glm-flash", "subset_exp": "glm-flash", "write_up": "sonnet"},
    "mimo": dict.fromkeys(STAGES, "mimo-pro"),
    "deepseek": dict.fromkeys(STAGES, "deepseek-flash"),
    "sonnet": dict.fromkeys(STAGES, "sonnet"),
}
GUIDANCE = OutputGuidance(
    format="paper",
    max_words=1200,
    required_sections=["Abstract", "Method", "Results", "Limitations", "References"],
    emphasis="Say plainly what the crude loop did and did not establish; report a negative result as one.",
    constraints=["forbid: state of the art", "forbid: breakthrough"],
)
LITERATURE_GUIDANCE = GUIDANCE.model_copy(update={  # with a literature review: a related-work section, and room for it
    "max_words": 1700,
    "required_sections": ["Abstract", "Related work", "Method", "Results", "Limitations", "References"],
})  # fmt: skip
REASONING = {"effort": "minimal"}  # every generator, so arms differ by model and not by thinking budget


def initial_state_from(run_id: str) -> dict:
    """The state after the baseline gate of a finished run: the recorded baseline, for the arms to share."""
    source = ROOT / "runs" / run_id
    saver = sqlite_checkpointer(source / "checkpoints.sqlite")
    values = saver.get_tuple(run_config(run_id)).checkpoint["channel_values"]
    return {
        "baseline": values["baseline"],
        "verdicts": {"baseline": values["verdicts"]["baseline"]},
        "stage_results": values["stage_results"][:1],
        "artifacts": {"baseline": values["artifacts"]["baseline"], "baseline_raw": values["artifacts"]["baseline_raw"]},
        "trail": ["baseline", "baseline_gate"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--datasets", default="analytical,airfoil")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--ideas", type=int, default=3)
    ap.add_argument("--run", type=int, default=2, help="how many ideas to run on the subset")
    ap.add_argument("--max-usd", type=float, default=3.0)
    ap.add_argument("--max-wall", type=int, default=7200)
    ap.add_argument("--generator", choices=sorted(GENERATORS), default=None, help="one model for every stage")
    ap.add_argument("--arm", choices=sorted(ARMS), default=None, help="a per-stage generator preset (docs/04 T9)")
    ap.add_argument("--from-run", default=None, help="start at the ideas stage from this run's recorded baseline")
    ap.add_argument("--max-tokens", type=int, default=8000, help="output-token cap per generator call")
    ap.add_argument(
        "--literature",
        default=None,
        help="a finished topic run (runs/<id>/): its verified section is "
        "the paper's related work and informs the ideas; its cited sources are the paper's references",
    )
    ap.add_argument(
        "--protocol",
        nargs="?",
        const="docs/results/tree_explain_protocol_spec.json",
        default=None,
        help="run a registered protocol (a ProtocolSpec JSON; default the tree-explain one) after the idea stages",
    )
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    check_available()
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    per_stage = ARMS[args.arm] if args.arm else dict.fromkeys(STAGES, args.generator or "glm-flash")
    spec = RunSpec(
        run_id=args.run_id,
        problem=ProblemSpec(
            parent_id="2510.24815", repo_url="https://github.com/ThalesGroup/treehfd",
            repo_commit="dd021526a9c97424334361d97cb88efe6f4e1b39", metric="residual_mse_pct",
            datasets=args.datasets.split(","),
            subset={"n_seeds": args.seeds, "n_ideas": args.ideas, "n_run": args.run},
        ),
        guidance=LITERATURE_GUIDANCE if args.literature else GUIDANCE,
        budget=Budget(max_usd=args.max_usd, max_wall_seconds=args.max_wall),
        models=per_stage,
    )  # fmt: skip
    ledger = Ledger.for_run(args.run_id, root=ROOT / "data" / "ledger", resume=args.resume)
    budget = spec.budget.model_copy()
    run_dir = ROOT / "runs" / args.run_id
    initial, start_at = None, None
    if args.from_run and not args.resume:
        source = ROOT / "runs" / args.from_run
        initial, start_at = initial_state_from(args.from_run), "ideate"
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        shutil.copy(source / "artifacts" / "baseline.json", run_dir / "artifacts" / "baseline.json")
        shutil.copy(source / "artifacts" / "baseline.json", run_dir / "artifacts" / "baseline_raw.json")
        shutil.copy(source / "retrieved.jsonl", run_dir / "retrieved.jsonl")
    elif args.from_run:
        start_at = "ideate"
    lit = None
    if args.literature:
        lit = literature_context.prepare(run_dir, ROOT / "runs" / args.literature, write=not args.resume)
    references.retrieve_seed_references(run_dir)
    generators = {
        name: OpenRouterGenerator(
            name, GENERATORS[name], ledger=ledger, budget=budget, max_tokens=args.max_tokens, reasoning=REASONING
        )  # fmt: skip
        for name in set(per_stage.values())
    }
    deps = LoopDeps(
        spec=spec, target=target,
        generator=ByStage({stage: generators[name] for stage, name in per_stage.items()}),
        judge=cheap_path(ledger=ledger, budget=budget), sandbox=run_script, budget=budget, run_dir=run_dir,
        data_dir=ROOT / "data" / "raw" / "datasets", ledger=ledger,
    )  # fmt: skip
    if lit:
        deps.extra["literature"] = lit
    if args.protocol:
        proto = ProtocolSpec.model_validate_json((ROOT / args.protocol).read_text(encoding="utf-8"))
        deps.extra["protocol"] = {"spec": proto, "root": ROOT}
    with keep_awake():  # a standby in the middle of a run makes its wall-clock limits jump (vera/keepawake.py)
        state = run_loop(deps, resume_run=args.resume, start_at=start_at, initial_state=initial)
    report = write_report(deps, state, ROOT)  # data/results/run_<id>.json: per-stage cost table and outcome
    stop = state.get("stop")
    print(f"arm: {args.arm or args.generator or 'glm-flash'}; trail: {' > '.join(state['trail'])}")
    print(f"stopped: {stop['stage'] + ': ' + stop['reason'] if stop else 'no, run complete'}")
    print(f"report: {report.relative_to(ROOT)}")
    print(f"spent: ${deps.budget.spent_usd:.4f} of ${args.max_usd}; wall {deps.budget.elapsed_seconds}s; "
          f"ledger {ledger.path.relative_to(ROOT)}")  # fmt: skip


if __name__ == "__main__":
    main()

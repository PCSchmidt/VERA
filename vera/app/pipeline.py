# ruff: noqa: E501
"""The pipeline the app runs for a user's topic: the literature stage, in phases (Increment 5).

Same stages and checks as `scripts/run_topic.py`, driven by a `RunRequest` instead of a topic file: scoping up to the user's
confirmation (`start`), the stages that follow (`continue`), and `resume` after a stop. The model key comes from the process
environment (the app's server hands it to the worker that way); nothing here writes it anywhere.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vera import audit
from vera.app.appbudget import STOP_FILE, AppBudget
from vera.backends.generator import OpenRouterGenerator
from vera.graph import run_config
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.literature import scoping
from vera.literature.deps import LitDeps
from vera.literature.graph import STAGE_NODES, _graph, continue_topic_run, rerun_from, start_topic_run
from vera.literature.parent import RepoLookup
from vera.literature.reading import GrobidParser, ParseCache, PdfFetcher
from vera.literature.retrieval import HttpCache, Retriever
from vera.schemas import Budget, RunRequest, RunSpec, Topic

DEFAULT_MODEL = (
    "sonnet",
    "anthropic/claude-sonnet-5.5",
)  # T9: Sonnet 5.5 for every stage; VERA_GENERATOR_MODEL overrides
REASONING = {"effort": "minimal"}
MAX_TOKENS = 8000
SCOPE_CAP_USD = 0.25  # spent on scoping before the user confirms the question


def generator_model() -> tuple[str, str]:
    override = os.environ.get("VERA_GENERATOR_MODEL")
    return (override.rsplit("/", 1)[-1], override) if override else DEFAULT_MODEL


LITERATURE_ONLY_HINT = (
    "This run produces a literature review only: the app cannot run experiments. Propose exactly one question, "
    "phrased as one question, that a literature review alone can answer. Do not propose an experiment or a "
    "companion study, and set empirical to false."
)


def make_spec(request: RunRequest) -> RunSpec:
    topic = Topic(id=request.run_id, text=request.topic, scope_hint=None if request.allow_experiments else LITERATURE_ONLY_HINT)
    return RunSpec(
        run_id=request.run_id, topic=topic, guidance=request.guidance,
        budget=Budget(max_usd=request.max_usd, max_wall_seconds=request.max_wall_seconds),
        models={"scope": generator_model()[0]},
    )  # fmt: skip


def real_deps(root: Path, request: RunRequest, *, resume: bool) -> LitDeps:
    """Dependencies with the real generator, judge, retrieval and PDF reading. Needs OPENROUTER_API_KEY in the environment."""
    spec = make_spec(request)
    run_dir = root / "runs" / request.run_id
    ledger = Ledger.for_run(request.run_id, root=root / "data" / "ledger", resume=resume)
    budget = AppBudget(**spec.budget.model_dump()).watch(run_dir)
    name, model = generator_model()
    generator = OpenRouterGenerator(
        name, model, ledger=ledger, budget=budget, max_tokens=MAX_TOKENS, reasoning=REASONING
    )
    deps = LitDeps(
        spec=spec, generator=generator, judge=cheap_path(ledger=ledger, budget=budget), budget=budget,
        run_dir=run_dir, ledger=ledger, scope_cap_usd=SCOPE_CAP_USD,
    )  # fmt: skip
    cache = root / "data" / "cache"
    deps.extra["retriever"] = Retriever(cache=HttpCache(cache / "http"))  # keyed sources join when their keys are set
    deps.extra["fetch_pdf"] = PdfFetcher(cache / "pdf")
    parser = GrobidParser()  # a parser failure falls back to the abstract, and the reading report says so
    deps.extra["parse_pdf"] = lambda pdf: ParseCache(cache / "parsed").parse(pdf, parser)
    deps.extra["parse_refs"] = lambda pdf: ParseCache(cache / "parsed").references(pdf, parser)
    deps.extra["repo_lookup"] = RepoLookup(HttpCache(cache / "http"))
    deps.extra["root"] = root
    return deps


def resume_node(deps: LitDeps) -> str:
    """The node a stopped run should run again from: the one whose checkpoint stands newest with a single node next."""
    graph = _graph(deps, STAGE_NODES)
    names = {n for n, _, _ in STAGE_NODES}
    for snap in graph.get_state_history(run_config(deps.spec.run_id)):
        if len(snap.next) == 1 and snap.next[0] in names:
            return snap.next[0]
    raise LookupError("no checkpoint of this run stands before a stage that could be run again")


def run_phase(deps: LitDeps, phase: str) -> dict:
    """Run one phase and return the final state. `resume` clears the user's Stop first."""
    if phase == "start":
        return start_topic_run(deps, extra_nodes=STAGE_NODES)
    if phase == "continue":
        return continue_topic_run(deps, extra_nodes=STAGE_NODES)
    if phase == "resume":
        stop = deps.run_dir / STOP_FILE
        stop.unlink(missing_ok=True)
        return rerun_from(deps, resume_node(deps), extra_nodes=STAGE_NODES)
    raise ValueError(f"unknown phase {phase!r}")


MIN_CONFIDENCE = 0.7


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def run_audit(deps: LitDeps, judge: Any = None) -> str:
    """The final audit of the finished literature section, as `scripts/audit_topic.py` does it: citations exist and each
    claim is supported by the passage it quotes. Writes `audit.md` and `artifacts/audit_report.json`; returns the light.
    The section's producer is `p3.synthesize`, so no judge grades its own text. Charged to the run's own budget."""
    run_dir = deps.run_dir
    judge = judge or cheap_path(ledger=deps.ledger, budget=deps.budget)

    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        verdict = verdict.model_copy(update={"producer_id": "p3.synthesize"})
        return verdict, verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE

    run = audit.run_literature_audit(
        (run_dir / "literature.md").read_text(encoding="utf-8"), _jsonl(run_dir / "claims.jsonl"),
        _jsonl(run_dir / "passages.jsonl"), _jsonl(run_dir / "retrieved.jsonl"), ask=ask, paper_id=deps.spec.run_id,
        paper_source="literature.md",
    )  # fmt: skip
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "audit_report.json").write_text(
        json.dumps(run.report.model_dump(mode="json"), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "audit.md").write_text(audit.render_markdown(run), encoding="utf-8")
    return run.report.overall


def confirm(run_dir: Path, question: str | None, who: str = "the app user") -> Any:
    """Record the user's confirmation (or edit) of the proposed question."""
    return scoping.confirm_scope(run_dir, who, question=question)


Deps = Callable[..., LitDeps]

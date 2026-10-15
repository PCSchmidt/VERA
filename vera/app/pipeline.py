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
from vera.audit import disagreement, sentences, sticky
from vera.backends.generator import OpenRouterGenerator
from vera.graph import run_config
from vera.judge.cheap_path import CONFIRM_NO, cheap_path, confirmer
from vera.ledger import Ledger
from vera.literature import coverage, scoping
from vera.literature.deps import LitDeps
from vera.literature.graph import STAGE_NODES, _graph, continue_topic_run, extend_run, rerun_from, start_topic_run
from vera.literature.paper_interpret import INTERPRET_NODES
from vera.literature.paper_stage import PAPER_NODES
from vera.literature.parent import RepoLookup
from vera.literature.reading import GrobidParser, ParseCache, PdfFetcher
from vera.literature.retrieval import HttpCache, Retriever
from vera.schemas import Budget, PaperRequest, RunRequest, RunSpec, Topic

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
    deps.extra["reference"] = confirmer(ledger=ledger, budget=budget)  # RSH-F-17: confirms a cheap no while writing
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


def paper_nodes() -> list:
    """The review's nodes followed by the paper's: the graph a paper is made (and resumed) in."""
    return [*STAGE_NODES, *PAPER_NODES, *INTERPRET_NODES]


def run_paper(deps: LitDeps, request: PaperRequest) -> dict:
    """Make a review paper from this finished review (RSH-F-12, APP-F-04): the paper's nodes run after the review's last
    node, in the same run, ledger and checkpoints, so nothing the review did is repeated. The paper's cap is its own:
    the run may spend at most `request.max_usd` more than its ledger shows now."""
    spent = sum(r.cost_usd for r in deps.ledger.records()) if deps.ledger is not None else deps.budget.spent_usd
    budget = deps.spec.budget.model_copy(update={"max_usd": spent + request.max_usd})
    deps.spec = deps.spec.model_copy(update={"budget": budget})
    deps.extra["paper_request"] = request
    return extend_run(deps, STAGE_NODES[-1][0], extra_nodes=paper_nodes())


def resume_paper(deps: LitDeps, request: PaperRequest, spent_before: float) -> dict:
    """Resume a stopped paper from its last checkpoint, with the same cap it was started with."""
    budget = deps.spec.budget.model_copy(update={"max_usd": spent_before + request.max_usd})
    deps.spec = deps.spec.model_copy(update={"budget": budget})
    deps.extra["paper_request"] = request
    (deps.run_dir / STOP_FILE).unlink(missing_ok=True)
    graph = _graph(deps, paper_nodes())
    names = {n for n, _, _ in [*PAPER_NODES, *INTERPRET_NODES]}
    node = next((s.next[0] for s in graph.get_state_history(run_config(deps.spec.run_id))
                 if len(s.next) == 1 and s.next[0] in names), None)  # fmt: skip
    if node is None:
        raise LookupError("no checkpoint of this paper stands before one of its stages")
    return rerun_from(deps, node, extra_nodes=paper_nodes())


MIN_CONFIDENCE = 0.7


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _confirming(deps: LitDeps, judge: Any, reference: Any) -> Any:
    """The reference judge that confirms an audit's "no" (AUD-F-13, `CONFIRM_NO`): the one given, else the real reference
    when the real judge is in use; none when a test passes its own judge and no reference."""
    if reference is not None or judge is not None:
        return reference
    return confirmer(ledger=deps.ledger, budget=deps.budget)


def _asker(judge: Any, reference: Any, confirmations: dict, producer: str, stored: dict | None = None) -> Callable:
    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        verdict = verdict.model_copy(update={"producer_id": producer})
        confident = verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE
        if reference is not None and question.id in CONFIRM_NO and confident and verdict.answer is False:
            kept = sticky.lookup(stored or {}, question.id, material)  # Increment 10: the write-time answer sticks
            if kept is not None:
                confirmations[verdict.trace_id] = kept
            else:
                (ref,) = reference.ask(material, [question])  # Increment 8: a "no" the reference must confirm
                confirmations[verdict.trace_id] = ref.model_copy(update={"producer_id": producer})
        return verdict, confident

    return ask


def run_audit(deps: LitDeps, judge: Any = None, reference: Any = None) -> str:
    """The final audit of the finished literature section, as `scripts/audit_topic.py` does it: citations exist and each
    claim is supported by the passage it quotes. Writes `audit.md` and `artifacts/audit_report.json`; returns the light.
    The section's producer is `p3.synthesize`, so no judge grades its own text. Charged to the run's own budget."""
    run_dir = deps.run_dir
    reference = _confirming(deps, judge, reference)
    judge = judge or cheap_path(ledger=deps.ledger, budget=deps.budget)
    confirmations: dict = {}
    stored_path = run_dir / "sentences.jsonl"
    ask = _asker(judge, reference, confirmations, "p3.synthesize",
                 sticky.index(_jsonl(stored_path)) if stored_path.exists() else {})  # fmt: skip

    markdown = (run_dir / "literature.md").read_text(encoding="utf-8")
    claims = _jsonl(run_dir / "claims.jsonl")
    run = audit.run_literature_audit(
        markdown, claims, _jsonl(run_dir / "passages.jsonl"), _jsonl(run_dir / "retrieved.jsonl"), ask=ask,
        paper_id=deps.spec.run_id, paper_source="literature.md",
    )  # fmt: skip
    records = {r["key"]: r for r in _jsonl(run_dir / "retrieved.jsonl")}
    ids = [c.get("id") or f"C{n}" for n, c in enumerate(claims, start=1)]  # reviews before 0.13 have no claim ids
    by_id = {i: c | {"title": records.get(c["source_key"], {}).get("title")} for i, c in zip(ids, claims, strict=True)}
    stored = run_dir / "sentences.jsonl"
    if stored.exists():
        entries = sentences.from_records(_jsonl(stored))
    else:
        body = markdown.partition("## Literature review")[2].split("\n## ")[0]
        entries = sentences.from_text([("", body)], ids)
    run, counts = _with_sentences(run, entries, by_id, ask, "sentences.jsonl" if stored.exists() else "literature.md",
                                  records=_jsonl(stored) if stored.exists() else [], confirmations=confirmations)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "audit_report.json").write_text(
        json.dumps(run.report.model_dump(mode="json"), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "audit.md").write_text(audit.render_markdown(run) + sentences.note(counts) + disagreement.note(counts["disagreements"], counts.get("unsettled", 0)), encoding="utf-8")
    return run.report.overall


def _with_sentences(
    run: Any, entries: list[dict], claims: dict, ask: Any, reference: str, *, records: list[dict] = (),
    inferences: list[dict] = (), confirmations: dict | None = None,
) -> tuple[Any, dict]:  # fmt: skip
    """The audit run with the sentence audit's findings added (AUD-F-12), judge disagreements with the write-time
    verdicts in `records` and `inferences` reported as warnings, not failures (AUD-F-13), and its light recomputed."""
    from vera.audit import overall_of  # noqa: PLC0415

    extra, counts = sentences.audit(entries, claims, ask, reference)
    findings, counts["disagreements"] = disagreement.reconcile(
        [*run.report.findings, *extra], list(records), list(inferences), confirmations
    )
    counts["unsettled"] = disagreement.count_unsettled(findings)
    report = run.report.model_copy(update={"findings": findings, "overall": overall_of(findings),
                                           "checks_run": [*run.report.checks_run, "sentence"]})  # fmt: skip
    return audit.AuditRun(report, run.claims), counts


def run_paper_audit(deps: LitDeps, judge: Any = None, reference: Any = None) -> str:
    """The paper's audit (AUD-F-11): the frozen literature audit on the paper's text, claims and wider passages, then
    every kept interpretation statement re-checked (`vera.audit.inference`). Writes `paper/audit.md` and
    `paper/audit_report.json`; returns the light. The evidence sections' producer is `p3.paper.write` and the
    interpretation's `p3.paper.interpret`; neither judges its own text. Charged to the run's own budget."""
    from vera.audit import overall_of  # noqa: PLC0415 - only papers need these

    run_dir, out = deps.run_dir, deps.run_dir / "paper"
    reference = _confirming(deps, judge, reference)
    judge = judge or cheap_path(ledger=deps.ledger, budget=deps.budget)
    confirmations: dict = {}

    saved = json.loads((out / "paper.json").read_text(encoding="utf-8")) if (out / "paper.json").exists() else {}
    stored = sticky.index([*(saved.get("sentences") or []), *(saved.get("inferences") or [])])

    def asker(producer: str):
        return _asker(judge, reference, confirmations, producer, stored)

    run = audit.run_literature_audit(
        (out / "paper.md").read_text(encoding="utf-8"), _jsonl(out / "claims.jsonl"), _jsonl(out / "passages.jsonl"),
        coverage.records(run_dir), ask=asker("p3.paper.write"), paper_id=f"{deps.spec.run_id} (paper)",
        paper_source="paper/paper.md",
    )  # fmt: skip
    doc = json.loads((out / "paper.json").read_text(encoding="utf-8"))
    records = {r["key"]: r for r in coverage.records(run_dir)}  # the review's, and any the targeted search added
    claims = {c["id"]: f"{c['claim']} (source: {records[c['source_key']]['title']})" for c in doc["claims"]}
    source_of = {c["id"]: c["source_key"] for c in doc["claims"]}
    extra = sentences.audit_inferences(doc["inferences"], claims, source_of, asker("p3.paper.interpret"))
    findings = [*run.report.findings, *extra]
    report = run.report.model_copy(update={"findings": findings, "overall": overall_of(findings),
                                           "checks_run": [*run.report.checks_run, "inference"]})  # fmt: skip
    run = audit.AuditRun(report, run.claims)
    by_id = {c["id"]: c | {"title": records.get(c["source_key"], {}).get("title")} for c in doc["claims"]}
    if doc.get("sentences"):
        entries = sentences.from_records(doc["sentences"])
    else:  # a paper made before 0.13
        evidence = [(s["heading"], s["text"]) for s in doc["sections"] if s["kind"] == "evidence"]
        entries = sentences.from_text(evidence, [c["id"] for c in doc["claims"]])
    run, counts = _with_sentences(run, entries, by_id, asker("p3.paper.write"), "paper/paper.json",
                                  records=doc.get("sentences") or [], inferences=doc["inferences"],
                                  confirmations=confirmations)
    report = run.report
    (out / "audit_report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    n_kept = sum(1 for i in doc["inferences"] if i["status"] == "pass")
    note = (
        f"\nInterpretation statements re-checked: {n_kept} (judged to follow from the claims they name; "
        "not checked against quotes).\n"
    )
    (out / "audit.md").write_text(audit.render_markdown(run) + note + sentences.note(counts) + disagreement.note(counts["disagreements"], counts.get("unsettled", 0)), encoding="utf-8")
    return report.overall


def confirm(run_dir: Path, question: str | None, who: str = "the app user") -> Any:
    """Record the user's confirmation (or edit) of the proposed question."""
    return scoping.confirm_scope(run_dir, who, question=question)


Deps = Callable[..., LitDeps]

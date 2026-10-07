# ruff: noqa: E501
"""The loop's final gate: the audit of its own write-up (RSH-F-05).

`audit_node` runs `vera.audit.run_audit` on `paper.md` against the run's `results.json` and retrieval log, writes the
`AuditReport` (JSON and a readable markdown copy), and records the stage result. The audit's gate is a rule, not a
model: red (any `fail` finding) means the run is not a success, so the node stops the run with the failing findings in
the reason and the audit stage is not listed as completed. Amber (something unconfirmed) and green pass, and the
report says which.

The judge calls the audit makes (`cite.contains_entry`, `num.claim_consistent`) go through the shared cheap path and
are logged to gates.jsonl with the write-up as the producer of the material, so a judge cannot grade its own text.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

from vera import audit
from vera.audit.bibliography import SourceLookup
from vera.loop import references
from vera.loop.protocol_stage import idea_sources
from vera.loop.stages import LoopDeps, _stop, _write_json, ask_gate, finish, stage_result
from vera.schemas import Question, Verdict

WRITE_UP_PRODUCER = "p3.write_up"
AUDIT_PRODUCER = "p1.audit"
AUDIT_GATE = "p1.audit_gate"


def audit_gate_verdict(overall: str) -> Verdict:
    """The rule's verdict on the report: a different component from the audit that produced it (no self-grading)."""
    return Verdict(
        question_id="loop.audit_clean", answer=overall != "red", confidence=1.0, confidence_source=None,
        backend="rule", escalated=False, cost_usd=0.0, latency_ms=0, trace_id=uuid.uuid4().hex,
        producer_id=AUDIT_PRODUCER, judge_id=AUDIT_GATE,
    )  # fmt: skip


def audit_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        text = (deps.run_dir / "paper.md").read_text(encoding="utf-8")
        results_json = json.loads((deps.run_dir / "artifacts" / "results.json").read_text(encoding="utf-8"))
        lookup = deps.extra.get("lookup") or SourceLookup()

        def ask(question: Question, material: str) -> tuple[Verdict, bool]:
            return ask_gate(deps, "audit", question, material, None, state, producer=WRITE_UP_PRODUCER)

        fig_file = deps.run_dir / "figures" / "figures.json"
        figs = json.loads(fig_file.read_text(encoding="utf-8")) if fig_file.exists() else None
        try:
            methods = idea_sources(state, deps)  # the code of each idea with a valid run
        except (KeyError, FileNotFoundError):
            methods = {}
        ran_ideas = {i["name"]: i["description"] for i in state.get("ideas", []) if i["name"] in methods}
        records_file = deps.run_dir / "retrieved.jsonl"
        records = (
            [json.loads(ln) for ln in records_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if records_file.exists()
            else []
        )
        run = audit.run_audit(
            text, results_json, references.load_references(deps.run_dir), ask=ask, lookup=lookup,
            paper_id=deps.spec.run_id, paper_source="paper.md", target=deps.target, figures=figs, basis=True,
            methods=methods or None, ideas=ran_ideas or None, records=records, search=deps.extra.get("search"),
        )  # fmt: skip
        report = run.report
        artifact = _write_json(deps, "audit_report", report.model_dump(mode="json"))
        (deps.run_dir / "audit.md").write_text(audit.render_markdown(run), encoding="utf-8")
        counts = {s: float(sum(f.severity == s for f in report.findings)) for s in ("fail", "warn", "info")}
        gate = audit_gate_verdict(report.overall)
        decision = "reject" if report.overall == "red" else "accept"
        sr = stage_result(deps, "audit", artifact, gate, decision, {**counts, "claims": float(len(run.claims))})
        update = {"verdicts": {"audit_clean": gate.model_dump(mode="json")}, "stage_results": [sr],
                  "artifacts": {"audit": artifact}, "trail": ["audit"]}  # fmt: skip
        if report.overall == "red":
            fails = [f.summary for f in report.findings if f.severity == "fail"]
            update |= _stop("audit", f"gate: audit failed with {len(fails)} failing finding(s): {fails[:3]}")
        return finish(update)

    return node

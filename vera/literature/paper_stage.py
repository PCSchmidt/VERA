# ruff: noqa: E501
"""Paper stage nodes (RSH-F-12, RSH-F-14): a review paper from a finished review, appended to the topic graph on request.

    paper_widen ─► paper_outline ─► paper_write ─► paper_verify ─► (interpretation, audit)

The nodes run after the review's last node through `graph.extend_run`, so the review's stages, verdicts and spend stay
as they are and are never repeated. Everything the paper writes is in `runs/<run_id>/paper/`; the review's files are
read, never changed. The producer is `p3.paper.write`; every verdict on its text comes from the judge path.

The paper's options (`PaperRequest`: length, emphasis, cap) are in `deps.extra["paper_request"]`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from vera.literature import coverage, paper, paper_evidence, sentence_checks, synthesis
from vera.literature.deps import LitDeps
from vera.literature.stages import _confirmed_question
from vera.literature.synthesis_stage import verify_sentences
from vera.loop.stages import _extract_json, _stop, stage_result
from vera.schemas import PaperDocument, PaperRequest, PaperSection, RetrievalStats, SourceRecord

MIN_PAPER_CLAIMS = 15  # fewer, and the paper would be the review with padding
COMPONENT = "p3.paper.write"


def paper_dir(deps: LitDeps) -> Path:
    return deps.run_dir / paper_evidence.PAPER_DIR


def request(deps: LitDeps) -> PaperRequest:
    return deps.extra.get("paper_request") or PaperRequest(max_usd=deps.spec.budget.max_usd)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _records(deps: LitDeps) -> dict[str, dict]:
    return {r["key"]: r for r in coverage.records(deps.run_dir)}  # the review's, and any the targeted search added


def _passages(deps: LitDeps) -> list[dict]:
    return _jsonl(paper_dir(deps) / "passages.jsonl")


def _write(deps: LitDeps, name: str, data: object) -> str:
    path = paper_dir(deps) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return path.relative_to(deps.run_dir).as_posix()


def widen_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        _confirmed_question(deps)
        if not (deps.run_dir / "literature.md").exists():
            return _stop("paper", "there is no finished review to make a paper from")
        parse = deps.extra["parse_pdf"]
        req = request(deps)
        targets = coverage.named_targets(_confirmed_question(deps), req.emphasis)  # RSH-F-16: works the paper names
        review_records = {r["key"]: r for r in _jsonl(deps.run_dir / "retrieved.jsonl")}
        report, added = coverage.lookup(targets, review_records, deps.extra.get("retriever"), question=_confirmed_question(deps))
        coverage.write(paper_dir(deps), report, added)
        summary = paper_evidence.widen(deps.run_dir, deps.extra["fetch_pdf"], parse, added=added)
        _write(deps, "request.json", request(deps).model_dump(mode="json"))
        return {"paper_evidence": summary, "trail": ["paper_widen"]}

    return node


def outline_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question, req = _confirmed_question(deps), request(deps)
        records, passages = _records(deps), _passages(deps)
        review = (deps.run_dir / "literature.md").read_text(encoding="utf-8").partition("## References")[0]
        reply = deps.generator.generate(
            paper.SYSTEM, paper.outline_prompt(question, review, records, passages, req.emphasis), component=COMPONENT
        )
        title, themes = paper.parse_outline(_extract_json(reply, "{", "}"))
        kept, dropped = [], []
        for t in themes:
            (kept if paper.theme_supported(paper.theme_passages(t, passages)) else dropped).append(t)
        _write(deps, "outline.json", {"title": title, "themes": kept, "dropped": dropped})
        if not title or len(kept) < paper.MIN_THEMES:
            return _stop("paper", f"the outline has {len(kept)} themes the evidence supports (need {paper.MIN_THEMES})")
        return {"paper_outline": {"title": title, "themes": kept}, "trail": ["paper_outline"]}

    return node


def section_plan(req: PaperRequest, themes: list[dict], passages: list[dict]) -> list[tuple[str, str, list[dict], int]]:
    """(heading, purpose, the passages the writer is shown, words) per evidence section. Deterministic, so the verify
    step (and a resumed run) recovers exactly the passages each section was drafted from."""
    per_theme = int(req.length_words * paper.FINDINGS_SHARE / len(themes))
    plan = [
        (paper.INTRO, paper.INTRO_PURPOSE, passages[: paper.THEME_PASSAGES], int(req.length_words * paper.INTRO_SHARE))
    ]
    return plan + [
        (t["heading"], paper.findings_purpose(t), paper.theme_passages(t, passages), per_theme) for t in themes
    ]


def write_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question, req = _confirmed_question(deps), request(deps)
        records, passages = _records(deps), _passages(deps)
        drafts = []
        for heading, purpose, selected, words in section_plan(req, state["paper_outline"]["themes"], passages):
            reply = deps.generator.generate(
                paper.SYSTEM,
                paper.section_prompt(question, heading, purpose, selected, records, words, req.emphasis),
                component=COMPONENT,
            )
            drafts.append({"heading": heading, "paragraphs": sentence_checks.parse_typed(_extract_json(reply, "{", "}"))})
        _write(deps, "draft.json", drafts)
        if not any(d["paragraphs"] for d in drafts):
            return _stop("paper", "the model's replies held no usable section")
        return {"paper_draft": drafts, "trail": ["paper_write"]}

    return node


def verify_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        records, passages = _records(deps), _passages(deps)
        sections, verdicts, stats, logs = [], [], {}, []
        shown = {h: sel for h, _, sel, _ in section_plan(request(deps), state["paper_outline"]["themes"], passages)}
        for d in state["paper_draft"]:
            checked = verify_sentences(
                deps, state, question, d["paragraphs"], records, passages, stage="paper", component=COMPONENT,
                cache_file=paper_dir(deps) / "claims_judged.jsonl", seed_caches=(deps.run_dir / "claims_judged.jsonl",),
                repair_passages=shown.get(d["heading"], passages[: paper.THEME_PASSAGES]), heading=d["heading"],
            )  # fmt: skip
            verdicts += checked.verdicts
            logs.append(checked.log)
            text, claims = synthesis.assemble(checked.paragraphs)
            for c in claims:
                c["locator"] = (synthesis.matched_passage(c, passages) or {}).get("locator", "?")
            sections.append({"heading": d["heading"], "text": text, "claims": claims})
            for k, v in checked.stats.items():
                stats[k] = stats.get(k, 0) + v
        claims = sentence_checks.mark_same_quotes(paper.number_claims(sections))
        sentences = []
        for s, log in zip(sections, logs, strict=True):
            sentences += sentence_checks.sentence_records(log, [c["id"] for c in s["claims"]], s["heading"], len(sentences))
        themes_with_claims = sum(1 for s in sections[1:] if s["claims"])
        n_cited = len({c.source_key for c in claims})
        stats |= {"n_claims": len(claims), "n_sources_cited": n_cited, "themes_with_claims": themes_with_claims,
                  "distinct_quotes": sentence_checks.distinct_quotes(claims)}  # fmt: skip
        artifact = _write(deps, "verify.json", {"stats": stats, "sections": sections,
                                                "sentences": [s.model_dump(mode="json") for s in sentences]})  # fmt: skip
        why = None
        if len(claims) < MIN_PAPER_CLAIMS:
            why = f"only {len(claims)} claims survived the checks (need {MIN_PAPER_CLAIMS})"
        elif themes_with_claims < paper.MIN_THEMES:
            why = f"only {themes_with_claims} findings sections kept a claim (need {paper.MIN_THEMES})"
        sr = stage_result(deps, "paper", artifact, verdicts, "reject" if why else "accept",
                          {k: float(v) for k, v in stats.items()}, reason=why)  # fmt: skip
        if why:
            return {"stage_results": [sr], "trail": ["paper_verify"]} | _stop("paper", f"gate: {why}")
        doc = build_document(deps, state, question, sections, claims, records, sentences)
        return {"paper": doc.model_dump(mode="json"), "stage_results": [sr], "trail": ["paper_verify"]}

    return node


def build_document(
    deps: LitDeps, state: dict, question: str, sections: list[dict], claims: list, records: dict,
    sentences: list | None = None,
) -> PaperDocument:
    """The paper so far: introduction, method, findings, threats; written to paper/paper.md, paper.json, claims.jsonl."""
    stats = RetrievalStats.model_validate(state["section"]["retrieval_stats"])
    reading_summary = state.get("paper_evidence") or json.loads((paper_dir(deps) / "reading.json").read_text("utf-8"))
    models = paper.models_used(deps.ledger.path) if deps.ledger is not None else {}
    n_cited = len({c.source_key for c in claims})
    distinct = sentence_checks.distinct_quotes(claims)
    method = paper.method_section(question, stats, reading_summary, len(claims), n_cited, models, distinct)
    parts = [PaperSection(heading=paper.INTRO, kind="evidence", text=sections[0]["text"]),
             PaperSection(heading=paper.METHOD, kind="record", text=method)]  # fmt: skip
    parts += [PaperSection(heading=s["heading"], kind="evidence", text=s["text"]) for s in sections[1:] if s["text"]]
    named = coverage.threats_note(paper_dir(deps), reading_summary)
    parts.append(PaperSection(heading=paper.THREATS, kind="record", text=paper.threats_section(stats, reading_summary, named)))
    cited = sorted({c.source_key for c in claims}, key=lambda k: int(k[1:]))
    sources = [SourceRecord(key=k, id=records[k]["id"], title=records[k]["title"], authors=records[k].get("authors", []),
                            year=records[k].get("year"), source=records[k]["source"], url=records[k]["url"])
               for k in cited]  # fmt: skip
    evidence_stats = {k: int(reading_summary[k]) for k in ("n_full_text", "n_abstract_only", "n_passages")}
    evidence_stats["n_passages_cited"] = len({(c.source_key, c.locator) for c in claims})
    evidence_stats |= {"distinct_quotes": distinct, "claim_sources": n_cited}
    doc = PaperDocument(run_id=deps.spec.run_id, question=question, title=state["paper_outline"]["title"], sections=parts,
                        claims=claims, inferences=[], sources=sources, retrieval_stats=stats, evidence_stats=evidence_stats,
                        sentences=sentences or [])  # fmt: skip
    write_document(deps, doc, records)
    return doc


def write_document(deps: LitDeps, doc: PaperDocument, records: dict) -> None:
    out = paper_dir(deps)
    (out / "paper.md").write_text(paper.render(doc.title, doc.sections, doc.claims, records), encoding="utf-8")
    (out / "paper.json").write_text(doc.model_dump_json(indent=1), encoding="utf-8")
    (out / "claims.jsonl").write_text(
        synthesis.dump_jsonl([c.model_dump(mode="json") for c in doc.claims]), encoding="utf-8"
    )


PAPER_NODES = [
    ("paper_widen", "paper", widen_node),
    ("paper_outline", "paper", outline_node),
    ("paper_write", "paper", write_node),
    ("paper_verify", "paper", verify_node),
]

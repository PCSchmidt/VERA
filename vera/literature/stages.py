"""Retrieval stage nodes: queries from the confirmed question, retrieval, and the relevance screen.

    queries ─► retrieve ─► screen          (all three belong to the `retrieve` stage)

The generator writes a handful of short queries from the confirmed question; the retriever (Crossref and arXiv, T5)
fetches candidates for each; `merge_records` deduplicates and ranks them and the log `retrieved.jsonl` records every
candidate with the query and rank that found it (the log the final audit matches citations against). The relevance
screen asks the cheap judge path one question per candidate (`lit.relevant`, title and abstract only) and keeps the
confident "yes" answers; each verdict is appended to `screen.jsonl` as it is made, so a crash or a rerun never pays for
the same candidate twice.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable

from vera.audit.bibliography import LookupUnavailable
from vera.literature import questions, reading, retrieval, scoping
from vera.literature.deps import LitDeps
from vera.loop.stages import _extract_json, _stop, _write_json, ask_gate, stage_result
from vera.schemas import Verdict

N_QUERIES = 5
MAX_RECORDS = 60  # candidates kept in the log (best ranked first); bounds the screen's cost
MIN_RELEVANT = 5  # fewer than this and the literature stage stops: a review needs something to read

QUERY_SYSTEM = (
    "You are a research librarian. Reply only with what is asked, in the requested format. Never invent papers."
)


def query_prompt(question: str) -> str:
    return (
        f"Research question: {question}\n\n"
        f"Write {N_QUERIES} different short search queries (3 to 8 words each, no quotation marks or operators) that "
        "together would find the papers a literature review of this question should read: the methods by name, the "
        "key concepts, synonyms, and the neighbouring problems it builds on. Do not repeat the whole question.\n\n"
        'Reply with a JSON list of strings, for example ["query one", "query two"].'
    )


def parse_queries(reply: str) -> list[str]:
    data = _extract_json(reply, "[", "]")
    if not isinstance(data, list):
        return []
    seen: list[str] = []
    for q in data:
        q = " ".join(str(q).replace('"', " ").split())
        if q and q.lower() not in {s.lower() for s in seen}:
            seen.append(q)
    return seen[:N_QUERIES]


def _confirmed_question(deps: LitDeps) -> str:
    scoped = scoping.read_scope(deps.run_dir)
    if scoped is None or scoped.status == "proposed":
        raise scoping.ScopeNotConfirmedError("retrieval needs a confirmed question")
    return scoped.question


def queries_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        queries = parse_queries(deps.generator.generate(QUERY_SYSTEM, query_prompt(question), component="p3.retrieve"))
        if not queries:
            return _stop("retrieve", "the model's reply held no usable search queries")
        artifact = _write_json(deps, "queries", {"question": question, "queries": queries})
        return {"queries": queries, "artifacts": {"queries": artifact}, "trail": ["queries"]}

    return node


def retrieve_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        retriever = deps.extra["retriever"]
        hits: list[dict] = []
        try:
            for q in state["queries"]:
                hits += retriever(q)
        except LookupUnavailable as exc:
            return _stop("retrieve", f"no bibliographic source answered: {exc}")
        records = retrieval.merge_records(hits)[:MAX_RECORDS]
        log = deps.run_dir / "retrieved.jsonl"
        log.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        artifact = _write_json(deps, "retrieved", {"n_hits": len(hits), "n_records": len(records)})
        return {"records": [r["key"] for r in records], "artifacts": {"retrieved": artifact},
                "trail": ["retrieve"]}  # fmt: skip

    return node


def _load_screen(path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {r["hash"]: r for r in rows}


def screen_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question_text = _confirmed_question(deps)
        records = [json.loads(ln) for ln in (deps.run_dir / "retrieved.jsonl").read_text("utf-8").splitlines() if ln]
        done = _load_screen(deps.run_dir / "screen.jsonl")
        verdicts: list[Verdict] = []
        kept, unsure = [], []
        for rec in records:
            q, material = questions.relevant(question_text, rec)
            h = hashlib.sha1(f"{rec['key']}|{material}".encode()).hexdigest()[:16]
            if h in done:
                v = Verdict.model_validate(done[h]["verdict"])
                confident = done[h]["confident"]
            else:
                v, confident = ask_gate(deps, "retrieve", q, material, None, state)
                with (deps.run_dir / "screen.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"hash": h, "key": rec["key"], "confident": confident,
                                         "verdict": v.model_dump(mode="json")}) + "\n")  # fmt: skip
            verdicts.append(v)
            if confident and v.answer is True:
                kept.append(rec["key"])
            elif not confident:
                unsure.append(rec["key"])
        artifact = _write_json(deps, "relevance", {"kept": kept, "unsure": unsure, "n_screened": len(records)})
        passed = len(kept) >= MIN_RELEVANT
        metrics = {"n_screened": float(len(records)), "n_kept": float(len(kept)), "n_unsure": float(len(unsure))}
        why = None if passed else f"only {len(kept)} relevant candidates (need {MIN_RELEVANT})"
        sr = stage_result(deps, "retrieve", artifact, verdicts, "accept" if passed else "reject", metrics, reason=why)
        update = {"kept": kept, "stage_results": [sr], "artifacts": {"retrieve": artifact}, "trail": ["screen"]}
        if not passed:
            update |= _stop("retrieve", f"gate: only {len(kept)} relevant candidates (need {MIN_RELEVANT})")
        return update

    return node


# ── reading ──────────────────────────────────────────────────────────────────────────────────────────

READ_TOP = 6  # candidates read in full (those with an open-access PDF); every kept candidate's abstract is used


def read_node(deps: LitDeps) -> Callable[[dict], dict]:
    """Abstracts for every kept candidate, full text for the top `READ_TOP` with a PDF, as ranked evidence passages."""

    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        queries = " ".join(state.get("queries", []))
        records = {r["key"]: r for r in (json.loads(ln) for ln in
                   (deps.run_dir / "retrieved.jsonl").read_text("utf-8").splitlines() if ln)}  # fmt: skip
        kept = [records[k] for k in state["kept"]]
        top = int(deps.extra.get("read_top", READ_TOP))
        fetch, parse = deps.extra["fetch_pdf"], deps.extra["parse_pdf"]
        passages: list[dict] = []
        report: list[dict] = []
        full = 0
        for rec in kept:
            entry = {"key": rec["key"], "title": rec["title"], "mode": "abstract", "n_passages": 0}
            abstract = reading.abstract_passage(rec)
            if abstract:
                passages.append(abstract)
            if full < top and rec.get("pdf_url"):
                started = time.monotonic()
                try:
                    pdf = fetch(rec["pdf_url"])
                    if pdf is None:
                        entry["reason"] = f"no PDF: {getattr(fetch, 'last_error', None) or 'unavailable'}"
                    else:
                        paragraphs = parse(pdf)
                        found = reading.build_passages(paragraphs, rec["key"])
                        best = reading.rank_passages(found, f"{question} {queries}")
                        if best:
                            passages += best
                            entry |= {"mode": "fulltext", "n_passages": len(best), "n_paragraphs": len(paragraphs)}
                            full += 1
                        else:
                            entry["reason"] = "the parser returned no usable body text"
                except Exception as exc:  # noqa: BLE001 - a parser or network failure falls back to the abstract
                    entry["reason"] = f"{type(exc).__name__}: {str(exc)[:120]}"
                entry["seconds"] = round(time.monotonic() - started, 1)
            entry["n_passages"] = sum(1 for p in passages if p["source_key"] == rec["key"])
            report.append(entry)
        log = deps.run_dir / "passages.jsonl"
        log.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in passages), encoding="utf-8")
        artifact = _write_json(deps, "reading", {"n_full_text": full, "n_abstract_only": len(kept) - full,
                                                 "papers": report})  # fmt: skip
        return {"passages": len(passages), "artifacts": {"reading": artifact}, "trail": ["read"],
                "read_report": report}  # fmt: skip

    return node


def read_gate_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        passages = [json.loads(ln) for ln in (deps.run_dir / "passages.jsonl").read_text("utf-8").splitlines() if ln]
        records = {r["key"]: r for r in (json.loads(ln) for ln in
                   (deps.run_dir / "retrieved.jsonl").read_text("utf-8").splitlines() if ln)}  # fmt: skip
        papers = []
        for entry in state["read_report"]:
            mine = [p for p in passages if p["source_key"] == entry["key"]]
            if mine:
                best = next((p for p in mine if p["kind"] == "fulltext"), mine[0])
                papers.append({"title": records[entry["key"]]["title"], "mode": entry["mode"], "best": best["text"]})
        q, material = questions.evidence_sufficient(question, papers)
        verdict, confident = ask_gate(deps, "read", q, material, None, state)
        passed = confident and verdict.answer is True
        artifact = state["artifacts"]["reading"]
        metrics = {"n_passages": float(state["passages"]), "n_papers": float(len(papers))}
        why = None if passed else "the judge did not find the evidence sufficient (or was not confident)"
        sr = stage_result(deps, "read", artifact, verdict, "accept" if passed else "reject", metrics, reason=why)
        update = {"stage_results": [sr], "artifacts": {"read": artifact}, "trail": ["read_gate"]}
        if not passed:
            update |= _stop("read", f"gate: {why}")
        return update

    return node

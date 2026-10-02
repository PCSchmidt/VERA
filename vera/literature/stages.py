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
from collections.abc import Callable

from vera.audit.bibliography import LookupUnavailable
from vera.literature import questions, retrieval, scoping
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

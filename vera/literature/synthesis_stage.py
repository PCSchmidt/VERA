"""Synthesis stage nodes: draft the section, then verify every claim, repair once, drop what still fails.

    synthesize ─► verify

`synthesize` is the producer: one generator call that drafts the section as sentences with claims, from the evidence
passages only. `verify` runs the checks of `vera.literature.synthesis` (source resolves, quote is real, the judge path
says the passage supports the claim), sends the failures back once for repair, re-checks the repairs, and removes
whatever still fails. The judge's verdicts are cached in `claims_judged.jsonl`, so a rerun never pays twice.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from vera.literature import anchoring, questions, synthesis
from vera.literature.deps import LitDeps
from vera.literature.stages import _confirmed_question, _load_screen
from vera.loop.stages import _extract_json, _stop, _write_json, ask_gate, stage_result
from vera.schemas import ClaimLink, LiteratureSection, SourceRecord, Verdict

MIN_CLAIMS = 5  # fewer surviving claims than this and there is no literature section to speak of
MAX_PASSAGES_IN_PROMPT = 120


def _records(deps: LitDeps) -> dict[str, dict]:
    path = deps.run_dir / "retrieved.jsonl"
    return {r["key"]: r for r in (json.loads(ln) for ln in path.read_text("utf-8").splitlines() if ln)}


def _passages(deps: LitDeps) -> list[dict]:
    path = deps.run_dir / "passages.jsonl"
    return [json.loads(ln) for ln in path.read_text("utf-8").splitlines() if ln][:MAX_PASSAGES_IN_PROMPT]


def synthesize_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        passages, records = _passages(deps), _records(deps)
        prompt = (
            synthesis.draft_prompt(question, passages, records, deps.spec.guidance.max_words) + anchoring.ANCHOR_RULE
        )
        reply = deps.generator.generate(synthesis.SYSTEM, prompt, component="p3.synthesize")
        paragraphs = synthesis.parse_sentences(_extract_json(reply, "{", "}"))
        if not paragraphs:
            return _stop("synthesize", "the model's reply held no usable literature section")
        artifact = _write_json(deps, "draft_section", {"paragraphs": paragraphs})
        return {"draft": paragraphs, "artifacts": {"draft_section": artifact}, "trail": ["synthesize"]}

    return node


def _judge(deps: LitDeps, state: dict, sentence: dict, records: dict, passages: list[dict]) -> tuple[Verdict, bool]:
    """One claim's verdict, cached by question wording, claim and passage."""
    passage = synthesis.matched_passage(sentence["claim"], passages)
    title = records[sentence["claim"]["source_key"]]["title"]
    q, material = questions.claim_supported(sentence["text"], passage, title)
    cache_file = deps.run_dir / "claims_judged.jsonl"
    h = hashlib.sha1(f"{q.text}|{material}".encode()).hexdigest()[:16]
    cached = _load_screen(cache_file).get(h)
    if cached:
        return Verdict.model_validate(cached["verdict"]), cached["confident"]
    v, confident = ask_gate(deps, "synthesize", q, material, None, state)
    with cache_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"hash": h, "confident": confident, "verdict": v.model_dump(mode="json")}) + "\n")
    return v, confident


def verify_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        records, passages = _records(deps), _passages(deps)
        sentences = [[dict(s) for s in para] for para in state["draft"]]
        loose = [s for para in sentences for s in para if not s["claim"]]
        stray = sum(1 for s in loose if synthesis.STRAY_ATTRIBUTION.search(s["text"]))
        sentences = [
            [s for s in para if s["claim"] or not synthesis.STRAY_ATTRIBUTION.search(s["text"])] for para in sentences
        ]  # an attribution with no claim is never checked, so it is removed
        verdicts: list[Verdict] = []

        def failures(items: list[dict]) -> dict[int, str]:
            """Index in `items` -> why it failed (deterministic checks first, then the judge)."""
            out: dict[int, str] = {}
            for i, s in enumerate(items):
                status, why = synthesis.check_claim(s["claim"], records, passages)
                if status == "fail":
                    out[i] = why
                    continue
                v, confident = _judge(deps, state, s, records, passages)
                verdicts.append(v)
                if not (confident and v.answer is True):
                    out[i] = "unsupported" if confident else "judge_unsure"
                    continue
                marker = anchoring.marker_problem(s["text"], s["claim"]["quote"])
                if marker:  # an editorial connective the quote does not contain: the sentence says more than it quotes
                    out[i] = f"unanchored: the sentence adds {marker!r}, which the quote does not say"
                    continue
                dangling = anchoring.dangling_reference(s["text"])
                if dangling:  # the sentence leans on an earlier one for its subject
                    out[i] = f"unanchored: the sentence refers back ({dangling!r}) instead of naming its subject"
                    continue
                qa, material = anchoring.quote_covers_claim(
                    s["text"], s["claim"]["quote"], records[s["claim"]["source_key"]]["title"]
                )
                a, a_confident = ask_gate(deps, "synthesize", qa, material, None, state)
                verdicts.append(a)
                if not (a_confident and a.answer is True):
                    out[i] = "unanchored: the quote alone does not state the claim" if a_confident else "judge_unsure"
            return out

        claimed = [s for para in sentences for s in para if s["claim"]]
        first = failures(claimed)
        stats = {"drafted": len(claimed), "failed_first": len(first), "repaired": 0, "removed": 0,
                 "stray_attributions_removed": stray}  # fmt: skip
        reasons: dict[str, int] = {}
        for why in first.values():
            reasons[why] = reasons.get(why, 0) + 1
        replacements: dict[int, dict] = {}  # index in `claimed` -> the repaired sentence
        if first:
            bad = [{**claimed[i], "why": why} for i, why in first.items()]
            reply = deps.generator.generate(
                synthesis.SYSTEM, synthesis.repair_prompt(question, bad, passages, records), component="p3.synthesize"
            )
            fixes = _extract_json(reply, "[", "]")
            fixes = fixes if isinstance(fixes, list) else []
            candidates: dict[int, dict] = {}
            for i, fix in zip(first, fixes, strict=False):
                parsed = synthesis.parse_sentences({"paragraphs": [[fix]]}) if isinstance(fix, dict) else []
                if parsed and parsed[0][0]["claim"]:
                    candidates[i] = parsed[0][0]
            order = list(candidates)
            still = failures([candidates[i] for i in order])
            for n, i in enumerate(order):
                if n not in still:
                    replacements[i] = candidates[i]
        stats["repaired"] = len(replacements)
        removed = {i for i in first if i not in replacements}
        stats["removed"] = len(removed)

        kept_paragraphs, n = [], 0
        for para in sentences:
            keep = []
            for s in para:
                if s["claim"]:
                    i, n = n, n + 1
                    if i in replacements:
                        keep.append(replacements[i])
                    elif i not in removed:
                        keep.append(s)
                else:
                    keep.append(s)
            if keep:
                kept_paragraphs.append(keep)
        text, claims = synthesis.assemble(kept_paragraphs)
        cited = sorted({c["source_key"] for c in claims}, key=lambda k: int(k[1:]))
        section = LiteratureSection(
            run_id=deps.spec.run_id, topic_id=deps.spec.topic.id, text=text,
            claims=[ClaimLink(claim=c["claim"], source_key=c["source_key"], quote=c["quote"], quote_check="pass",
                              locator=(synthesis.matched_passage(c, passages) or {}).get("locator", "?"))
                    for c in claims],
            sources=[SourceRecord(key=k, id=records[k]["id"], title=records[k]["title"], authors=records[k]["authors"],
                                  year=records[k].get("year"), source=records[k]["source"], url=records[k]["url"])
                     for k in cited],
        )  # fmt: skip
        rstats = anchoring.stats_from_state(state)
        section = section.model_copy(update={"retrieval_stats": rstats})
        markdown = anchoring.insert_note(synthesis.render(text, claims, records), anchoring.retrieval_note(rstats))
        (deps.run_dir / "literature.md").write_text(markdown, encoding="utf-8")
        rows = [c.model_dump(mode="json") for c in section.claims]
        (deps.run_dir / "claims.jsonl").write_text(synthesis.dump_jsonl(rows), encoding="utf-8")
        artifact = _write_json(deps, "literature", {"stats": stats, "failure_reasons": reasons,
                                                    "n_claims_kept": len(claims)})  # fmt: skip
        if not verdicts:
            return _stop("synthesize", "no claim passed the deterministic checks, so none reached the judge")
        passed = len(claims) >= MIN_CLAIMS
        why = None if passed else f"only {len(claims)} claims survived the checks (need {MIN_CLAIMS})"
        if passed:  # the last gate: does the checked section answer the question?
            q, material = questions.section_answers(question, text)
            v, confident = ask_gate(deps, "synthesize", q, material, None, state)
            verdicts.append(v)
            if not (confident and v.answer is True):
                passed, why = False, "the judge did not find that the section addresses the question"
        metrics = {k: float(v) for k, v in stats.items()} | {"n_claims_kept": float(len(claims))}
        sr = stage_result(deps, "synthesize", artifact, verdicts, "accept" if passed else "reject", metrics, reason=why)
        artifacts = {"synthesize": artifact, "literature": "literature.md"}
        update = {"section": section.model_dump(mode="json"), "stage_results": [sr], "artifacts": artifacts,
                  "trail": ["verify"]}  # fmt: skip
        if not passed:
            update |= _stop("synthesize", f"gate: {why}")
        return update

    return node

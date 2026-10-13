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
from dataclasses import dataclass, field
from pathlib import Path

from vera.literature import anchoring, questions, sentence_checks, synthesis
from vera.literature.deps import LitDeps
from vera.literature.stages import _confirmed_question, _load_screen
from vera.loop.stages import PRODUCERS, _extract_json, _stop, _write_json, ask_gate, stage_result
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
            synthesis.draft_prompt(question, passages, records, deps.spec.guidance.max_words)
            + anchoring.ANCHOR_RULE
            + sentence_checks.SENTENCE_RULE
        )
        reply = deps.generator.generate(synthesis.SYSTEM, prompt, component="p3.synthesize")
        paragraphs = sentence_checks.parse_typed(_extract_json(reply, "{", "}"))
        if not paragraphs:
            return _stop("synthesize", "the model's reply held no usable literature section")
        artifact = _write_json(deps, "draft_section", {"paragraphs": paragraphs})
        return {"draft": paragraphs, "artifacts": {"draft_section": artifact}, "trail": ["synthesize"]}

    return node


def _judge(
    deps: LitDeps, state: dict, sentence: dict, records: dict, passages: list[dict], *, stage: str = "synthesize",
    cache_file: Path | None = None, seed_caches: tuple[Path, ...] = (),
) -> tuple[Verdict, bool]:  # fmt: skip
    """One claim's verdict, cached by question wording, claim and passage. `seed_caches` are read, never written: the
    paper reuses the review's verdicts on the same claim and passage without changing the review's files."""
    passage = synthesis.matched_passage(sentence["claim"], passages)
    title = records[sentence["claim"]["source_key"]]["title"]
    q, material = questions.claim_supported(sentence["text"], passage, title)
    cache_file = cache_file or deps.run_dir / "claims_judged.jsonl"
    h = hashlib.sha1(f"{q.text}|{material}".encode()).hexdigest()[:16]
    for f in (cache_file, *seed_caches):
        cached = _load_screen(f).get(h)
        if cached:
            verdict = Verdict.model_validate(cached["verdict"])
            return verdict.model_copy(update={"producer_id": PRODUCERS[stage]}), cached["confident"]
    v, confident = ask_gate(deps, stage, q, material, None, state)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"hash": h, "confident": confident, "verdict": v.model_dump(mode="json")}) + "\n")
    return v, confident


@dataclass
class Verified:
    paragraphs: list[list[dict]]  # what survived: claim, synthesis and transition sentences, each with kind and ref
    stats: dict
    reasons: dict[str, int]  # why claims failed their first check
    verdicts: list[Verdict] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)  # every drafted sentence in reading order, kept or removed, and why


def _outcome(s: dict, status: str, reason: str | None, verdicts: list[Verdict]) -> dict:
    return {"ref": s["ref"], "text": s["text"], "kind": s["kind"], "premises": list(s.get("premises") or []),
            "status": status, "reason": reason, "verdicts": verdicts}  # fmt: skip


def verify_sentences(
    deps: LitDeps, state: dict, question: str, draft: list[list[dict]], records: dict, passages: list[dict], *,
    stage: str = "synthesize", component: str = "p3.synthesize", cache_file: Path | None = None,
    seed_caches: tuple[Path, ...] = (), repair_passages: list[dict] | None = None, heading: str = "",
) -> Verified:  # fmt: skip
    """The checks every drafted sentence goes through, for the review and the paper alike (RSH-F-15).

    Claim sentences: the source must resolve and the quote be verbatim in that source's passage; a quote that opens
    with a back-reference is widened to the sentence before it (or fails); the judge must say the passage supports the
    claim; the sentence may add no connective the quote lacks and may not lean on an earlier sentence; the judge,
    shown the quote only, must say it states the claim and that the claim says no more than it.

    Claim-free sentences: one that names a source or says what the evidence lacks is removed; a synthesis must name
    surviving claim sentences as premises, speak of several sources only with premises from two, and be judged to
    follow from them (the inference check); a transition must be judged to state no fact.

    Failures are repaired once (by `component`, the producer) and re-checked; what still fails is removed and counted,
    and every sentence's outcome is in `log`. Claims are always checked against all of `passages`; `repair_passages`,
    when given, is the evidence the claim-repair prompt shows (a paper section's own passages)."""
    sentences = sentence_checks.ensure_typed([[dict(s) for s in para] for para in draft])
    drafted = [s for para in sentences for s in para]
    outcome: dict[str, dict] = {}  # ref -> the sentence's outcome
    per: dict[str, list[Verdict]] = {}  # ref -> verdicts on it
    verdicts: list[Verdict] = []
    counts = {"stray_attributions_removed": 0, "absence_removed": 0, "quotes_widened": 0}

    def ask(q, material: str) -> tuple[Verdict, bool]:
        return ask_gate(deps, stage, q, material, None, state)

    def screened(s: dict) -> str | None:
        """Why a claim-free sentence is removed before any judge sees it: it names a source no quote supports, or it
        says what the evidence lacks (which the record sections state from the run's files)."""
        named = sentence_checks.names_a_source(s["text"])
        if named:
            return f"names a source without a claim: {named!r}"
        return sentence_checks.absence_problem(s["text"])

    for s in (s for s in drafted if not s["claim"]):
        why = screened(s)
        if why:
            counts["absence_removed" if why.startswith("absence") else "stray_attributions_removed"] += 1
            outcome[s["ref"]] = _outcome(s, "removed", why, [])
    sentences = [[s for s in para if s["ref"] not in outcome] for para in sentences]

    def failures(items: list[dict]) -> dict[int, str]:
        """Index in `items` -> why it failed (deterministic checks first, then the judge)."""
        out: dict[int, str] = {}
        for i, s in enumerate(items):
            mine = per.setdefault(s["ref"], [])
            status, why = synthesis.check_claim(s["claim"], records, passages)
            if status == "fail":
                out[i] = why
                continue
            if sentence_checks.leans_on_context(s["claim"]["quote"]):
                matched = synthesis.matched_passage(s["claim"], passages)
                wider = sentence_checks.widen_quote(s["claim"]["quote"], matched["text"]) if matched else None
                if not wider:
                    out[i] = "unanchored: the quote leans on context outside it"
                    continue
                s["claim"] = {**s["claim"], "quote": wider}
                counts["quotes_widened"] += 1
            v, confident = _judge(deps, state, s, records, passages, stage=stage, cache_file=cache_file,
                                  seed_caches=seed_caches)  # fmt: skip
            verdicts.append(v)
            mine.append(v)
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
            title = records[s["claim"]["source_key"]]["title"]
            qa, material = anchoring.quote_covers_claim(s["text"], s["claim"]["quote"], title)
            a, a_confident = ask(qa, material)
            verdicts.append(a)
            mine.append(a)
            if not (a_confident and a.answer is True):
                out[i] = "unanchored: the quote alone does not state the claim" if a_confident else "judge_unsure"
                continue
            qw, material = sentence_checks.within_quote(s["text"], s["claim"]["quote"], title)
            w, w_confident = ask(qw, material)
            verdicts.append(w)
            mine.append(w)
            if not (w_confident and w.answer is True):
                out[i] = "says more than its quote" if w_confident else "judge_unsure"
        return out

    claimed = [s for para in sentences for s in para if s["claim"]]
    first = failures(claimed)
    stats = {"drafted": len(claimed), "failed_first": len(first), "repaired": 0, "removed": 0}
    reasons: dict[str, int] = {}
    for why in first.values():
        reasons[why] = reasons.get(why, 0) + 1
    replacements: dict[int, dict] = {}  # index in `claimed` -> the repaired sentence
    if first:
        bad = [{**claimed[i], "why": why} for i, why in first.items()]
        shown = passages if repair_passages is None else repair_passages
        reply = deps.generator.generate(
            synthesis.SYSTEM, synthesis.repair_prompt(question, bad, shown, records), component=component
        )
        fixes = _extract_json(reply, "[", "]")
        fixes = fixes if isinstance(fixes, list) else []
        candidates: dict[int, dict] = {}
        for i, fix in zip(first, fixes, strict=False):
            parsed = synthesis.parse_sentences({"paragraphs": [[fix]]}) if isinstance(fix, dict) else []
            if parsed and parsed[0][0]["claim"]:
                candidates[i] = {**parsed[0][0], "kind": "claim", "ref": claimed[i]["ref"], "premises": []}
        order = list(candidates)
        still = failures([candidates[i] for i in order])
        for n, i in enumerate(order):
            if n not in still:
                replacements[i] = candidates[i]
    stats["repaired"] = len(replacements)
    removed = {i for i in first if i not in replacements}
    stats["removed"] = len(removed)
    for i, s in enumerate(claimed):
        if i in replacements:
            outcome[s["ref"]] = _outcome(replacements[i], "pass", None, per.get(s["ref"], []))
        elif i in removed:
            outcome[s["ref"]] = _outcome(s, "removed", first[i], per.get(s["ref"], []))
        else:
            outcome[s["ref"]] = _outcome(s, "pass", None, per.get(s["ref"], []))

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

    # claim-free sentences, now that the claims they may rest on are settled
    kept_claims = {s["ref"]: s for para in kept_paragraphs for s in para if s["claim"]}
    temp = {ref: f"C{k + 1}" for k, ref in enumerate(kept_claims)}  # local ids for the inference check's rules
    claim_text = {temp[r]: f'{c["text"]} (source: "{records[c["claim"]["source_key"]]["title"]}")'
                  for r, c in kept_claims.items()}  # fmt: skip
    source_of = {temp[r]: c["claim"]["source_key"] for r, c in kept_claims.items()}

    def loose_failure(s: dict) -> tuple[str | None, list[Verdict]]:
        if s["kind"] == "synthesis":
            if not s["premises"]:
                return "a synthesis names no premise", []
            missing = [p for p in s["premises"] if p not in kept_claims]
            if missing:
                return f"premise removed or unknown: {', '.join(missing)}", []
            ids = [temp[p] for p in s["premises"]]
            return sentence_checks.check_statement(s["text"], ids, claim_text, ask, source_of)
        q, material = sentence_checks.no_fact(s["text"], heading)
        v, confident = ask(q, material)
        if not confident:
            return "judge_unsure", [v]
        return (None if v.answer is True else "a transition that states a fact"), [v]

    loose = [s for para in kept_paragraphs for s in para if not s["claim"]]
    loose_bad: dict[str, str] = {}
    for s in loose:
        why, vs = loose_failure(s)
        verdicts += vs
        per.setdefault(s["ref"], []).extend(vs)
        if why:
            loose_bad[s["ref"]] = why
    loose_fixed: dict[str, dict] = {}
    if loose_bad:
        failed = [{**s, "why": loose_bad[s["ref"]]} for s in loose if s["ref"] in loose_bad]
        reply = deps.generator.generate(
            synthesis.SYSTEM, sentence_checks.repair_prompt(question, failed, list(kept_claims.values())),
            component=component,
        )  # fmt: skip
        fixes = _extract_json(reply, "[", "]")
        fixes = fixes if isinstance(fixes, list) else []
        for s, fix in zip(failed, fixes, strict=False):
            if not (isinstance(fix, dict) and (fix.get("text") or "").strip()):
                continue
            cand = sentence_checks.typed({"text": fix["text"].strip(), "claim": None}, {**fix, "ref": s["ref"]}, 0)
            if screened(cand):
                continue
            why, vs = loose_failure(cand)
            verdicts += vs
            per[s["ref"]].extend(vs)
            if why is None:
                loose_fixed[s["ref"]] = cand
    for s in loose:
        if s["ref"] in loose_fixed:
            outcome[s["ref"]] = _outcome(loose_fixed[s["ref"]], "pass", None, per[s["ref"]])
        elif s["ref"] in loose_bad:
            outcome[s["ref"]] = _outcome(s, "removed", loose_bad[s["ref"]], per[s["ref"]])
        else:
            outcome[s["ref"]] = _outcome(s, "pass", None, per[s["ref"]])
    final = []
    for para in kept_paragraphs:
        keep = [loose_fixed.get(s["ref"], s) for s in para
                if s["claim"] or s["ref"] not in loose_bad or s["ref"] in loose_fixed]  # fmt: skip
        if keep:
            final.append(keep)

    for kind in ("synthesis", "transition"):
        mine = [s for s in drafted if not s["claim"] and s["kind"] == kind]
        stats[f"{kind}_drafted"] = len(mine)
        stats[f"{kind}_removed"] = sum(1 for s in mine if outcome[s["ref"]]["status"] == "removed")
    stats["loose_repaired"] = len(loose_fixed)
    stats |= counts
    log = [outcome[s["ref"]] for s in drafted]
    return Verified(final, stats, reasons, verdicts, log)


def verify_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        records, passages = _records(deps), _passages(deps)
        checked = verify_sentences(deps, state, question, state["draft"], records, passages)
        stats, reasons, verdicts = checked.stats, checked.reasons, checked.verdicts
        text, claims = synthesis.assemble(checked.paragraphs)
        cited = sorted({c["source_key"] for c in claims}, key=lambda k: int(k[1:]))
        ids = [f"C{n}" for n in range(1, len(claims) + 1)]  # 0.13: review claims get ids, so synthesis can name them
        links = [ClaimLink(id=i, claim=c["claim"], source_key=c["source_key"], quote=c["quote"], quote_check="pass",
                           locator=(synthesis.matched_passage(c, passages) or {}).get("locator", "?"))
                 for i, c in zip(ids, claims, strict=True)]  # fmt: skip
        stats |= {"distinct_quotes": sentence_checks.distinct_quotes(links)}
        section = LiteratureSection(
            run_id=deps.spec.run_id, topic_id=deps.spec.topic.id, text=text,
            claims=sentence_checks.mark_same_quotes(links),
            sentences=sentence_checks.sentence_records(checked.log, ids, ""),
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
        sentence_rows = [s.model_dump(mode="json") for s in section.sentences]  # 0.13: the audit re-checks each
        (deps.run_dir / "sentences.jsonl").write_text(synthesis.dump_jsonl(sentence_rows), encoding="utf-8")
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

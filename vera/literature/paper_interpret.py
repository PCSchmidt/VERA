# ruff: noqa: E501
"""Interpretation sections and the abstract of a review paper (RSH-F-13, Increment 6; decided by Chris 2026-10-11).

    paper_interpret     (stage `interpret`, producer p3.paper.interpret)

The writer sees **only the verified claims** (id, claim, source title), never the passages, so nothing unverified can
enter as a premise. It drafts three sections, *Discussion*, *Conclusions* and *A research agenda*, as statements that
each name the claims they rest on. Every statement goes through `vera.audit.inference.check`: the deterministic rules,
then the judge (`paper.inference_follows`, a component other than the writer). Failures are repaired once; what still
fails, or what the judge is unsure of, is removed and kept on record in `paper/inferences.jsonl`.

The kept statements are shown in labelled sections ("Interpretation: ..."), each followed by its premises, `(C3, C9)`.
The abstract is written last, from the claims and the kept statements, and is checked the same way against all of them;
if it fails twice VERA writes a plain abstract from the run's counts instead.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from vera.audit import inference
from vera.literature import paper, sentence_checks
from vera.literature.deps import LitDeps
from vera.literature.paper_stage import _records, paper_dir, request, write_document
from vera.literature.stages import _confirmed_question
from vera.loop.stages import _extract_json, ask_gate, rule_verdict, stage_result
from vera.schemas import Inference, PaperDocument, PaperSection, Question, QuestionType, Verdict

COMPONENT = "p3.paper.interpret"
SECTIONS = {
    "Discussion": "What the claims, taken together, suggest about the question: where they agree, where they pull apart, and why that matters.",
    "Conclusions": "The answer to the question that the claims allow, stated no more strongly than they support, including what remains unanswered.",
    "A research agenda": "Studies or measurements that the gaps in these claims call for, each tied to the claims that show the gap.",
}
LABEL = "*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*"
INTERPRET_SHARE, ABSTRACT_WORDS = 0.20, 200
MIN_ABSTRACT_WORDS = 30  # a reply shorter than this is not an abstract
SYSTEM = (
    "You are a careful research writer. You draw conclusions only from the verified claims you are given, never from "
    "what you know otherwise, and you reply only with what is asked, in the requested format."
)


def claims_map(doc: PaperDocument, records: dict[str, dict]) -> dict[str, str]:
    return {c.id: f"{c.claim} (source: {records[c.source_key]['title']})" for c in doc.claims}


def interpret_prompt(question: str, claims: dict[str, str], words: int, emphasis: str | None) -> str:
    listed = "\n".join(f"{k}: {v}" for k, v in claims.items())
    sections = "\n".join(f'- "{h}": {why}' for h, why in SECTIONS.items())
    return (
        f"Research question: {question}\n\n"
        f"These claims were each verified against a quote from their source:\n{listed}\n\n"
        f"Write the interpretation sections of a review paper on the question, about {words} words in all:\n{sections}\n\n"
        "Write each section as statements. Every statement must name, as premises, the claim ids it rests on, and must "
        "follow from those claims alone: no fact, number, cause or generalisation they do not support, nothing stated "
        "more strongly than they allow. Do not name a source, author or system that its premises do not name, and do "
        "not cite sources directly. Saying plainly what the claims leave open is welcome."
        + (f" The reader asked for this emphasis: {emphasis}" if emphasis else "")
        + '\n\nReply with JSON: {"sections": [{"heading": "Discussion", "statements": [{"text": "...", "premises": ["C3", "C9"]}, ...]}, ...]}.'
    )


def repair_prompt(question: str, failed: list[dict], claims: dict[str, str]) -> str:
    listed = "\n".join(f"{k}: {v}" for k, v in claims.items())
    items = "\n".join(
        f"{i + 1}. [{f['why']}] {f['text']} (premises {', '.join(f['premises']) or 'none'})"
        for i, f in enumerate(failed)
    )
    return (
        f"Research question: {question}\n\nThese interpretation statements failed their checks. For each, rewrite it so "
        'that it follows from the claims it names (and names the right ones), or drop it with "text": null.\n\n'
        f"{items}\n\nClaims:\n{listed}\n\n"
        'Reply with JSON: a list in the same order, each {"text": "..." or null, "premises": ["C1", ...]}.'
    )


def parse_statements(data: object) -> list[tuple[str, dict]]:
    """(heading, {"text", "premises"}) for each statement under one of the three headings, in order."""
    out = []
    for sec in (data.get("sections") or []) if isinstance(data, dict) else []:
        heading = str(sec.get("heading") or "").strip() if isinstance(sec, dict) else ""
        if heading not in SECTIONS:
            continue
        for st in sec.get("statements") or []:
            if isinstance(st, dict) and str(st.get("text") or "").strip():
                premises = [str(p).strip() for p in st.get("premises") or [] if str(p).strip()]
                out.append(
                    (heading, {"text": inference.PREMISE_MARKER.sub("", str(st["text"])).strip(), "premises": premises})
                )
    return out


def render_section(statements: list[Inference]) -> str:
    sentences = [f"{s.text.rstrip('.')} ({', '.join(s.premises)})." for s in statements]
    return f"{LABEL}\n\n" + " ".join(sentences)


def abstract_question(abstract: str, claims: dict[str, str], kept: list[Inference]) -> tuple[Question, str]:
    listed = "\n".join(f"{k}: {v}" for k, v in claims.items())
    readings = "\n".join(f"{s.id}: {s.text}" for s in kept) or "(none)"
    material = f"Verified claims:\n{listed}\n\nInterpretation statements:\n{readings}\n\nAbstract:\n{abstract}"
    q = (
        "Does the abstract say only what the claims and interpretation statements above say, with no added fact, number "
        "or conclusion and nothing stated more strongly than they do? Answer false if it does not."
    )
    return Question(id="paper.abstract_faithful", type=QuestionType.BOOLEAN, text=q), material


def plain_abstract(question: str, doc: PaperDocument, n_kept: int) -> str:
    stats = doc.evidence_stats
    return (
        f"This review paper asks: {question} It rests on {len(doc.claims)} claims from {len(doc.sources)} sources, each "
        f"checked against a quote from its source, drawn from {stats.get('n_full_text', 0)} papers read in full and "
        f"{stats.get('n_abstract_only', 0)} read at the abstract. "
        + (f"Its interpretation sections offer {n_kept} statements judged to follow from those claims." if n_kept else
           "No interpretation statement passed its checks, so the paper offers none.")
    )  # fmt: skip


def interpret_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question, req = _confirmed_question(deps), request(deps)
        records = _records(deps)
        doc = PaperDocument.model_validate(state["paper"])
        claims = claims_map(doc, records)
        verdicts: list[Verdict] = []

        def ask(q: Question, material: str) -> tuple[Verdict, bool]:
            return ask_gate(deps, "interpret", q, material, None, state)

        source_of = {c.id: c.source_key for c in doc.claims if c.id}

        per: dict[int, list[Verdict]] = {}  # Increment 8 (AUD-F-13): each statement keeps its write-time verdicts

        def run_checks(text: str, premises: list[str], n: int) -> str | None:
            # Increment 7: the Increment 6 rules, "X and colleagues", the agreement rule, the clause-by-clause judge
            why, vs = sentence_checks.check_statement(text, premises, claims, ask, source_of)
            verdicts.extend(vs)
            per.setdefault(n, []).extend(vs)
            return why

        words = int(req.length_words * INTERPRET_SHARE)
        reply = deps.generator.generate(
            SYSTEM, interpret_prompt(question, claims, words, req.emphasis), component=COMPONENT
        )
        drafted = parse_statements(_extract_json(reply, "{", "}"))
        results = [(h, st, run_checks(st["text"], st["premises"], n)) for n, (h, st) in enumerate(drafted)]
        failed = [i for i, (_, _, why) in enumerate(results) if why]
        if failed:
            bad = [{**results[i][1], "why": results[i][2]} for i in failed]
            fixes = _extract_json(
                deps.generator.generate(SYSTEM, repair_prompt(question, bad, claims), component=COMPONENT), "[", "]"
            )
            for i, fix in zip(failed, fixes if isinstance(fixes, list) else [], strict=False):
                if isinstance(fix, dict) and str(fix.get("text") or "").strip():
                    st = {"text": inference.PREMISE_MARKER.sub("", str(fix["text"])).strip(),
                          "premises": [str(p).strip() for p in fix.get("premises") or []]}  # fmt: skip
                    why = run_checks(st["text"], st["premises"], i)
                    results[i] = (results[i][0], st, None if why is None else f"after repair: {why}")
        inferences = [Inference(id=f"I{n + 1}", section=h, text=st["text"], premises=st["premises"], verdicts=per.get(n, []),
                                status="pass" if why is None else "removed", reason=why)
                      for n, (h, st, why) in enumerate(results)]  # fmt: skip
        kept = [i for i in inferences if i.status == "pass"]

        abstract = None
        for _ in range(2):
            text = deps.generator.generate(
                SYSTEM, abstract_prompt(question, doc, claims, kept), component=COMPONENT
            ).strip()
            problem = inference.statement_problem(text, list(claims), claims | {i.id: i.text for i in kept})
            problem = problem or sentence_checks.names_a_source(text)
            if problem or len(text.split()) < MIN_ABSTRACT_WORDS:
                continue
            q, material = abstract_question(text, claims, kept)
            v, confident = ask(q, material)
            verdicts.append(v)
            if confident and v.answer is True:
                abstract = text
                break
        summary = PaperSection(
            heading="Abstract", kind="summary", text=abstract or plain_abstract(question, doc, len(kept))
        )

        interp = [PaperSection(heading=h, kind="interpretation", text=render_section([i for i in kept if i.section == h]))
                  for h in SECTIONS if any(i.section == h for i in kept)]  # fmt: skip
        body = [s for s in doc.sections if s.heading != paper.THREATS]
        threats = [s for s in doc.sections if s.heading == paper.THREATS]
        doc = doc.model_copy(update={"sections": [summary, *body, *interp, *threats], "inferences": inferences})
        doc = PaperDocument.model_validate(doc.model_dump())  # the schema's rules, on the finished paper
        write_document(deps, doc, records)
        rows = [i.model_dump(mode="json") for i in inferences]
        (paper_dir(deps) / "inferences.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )
        metrics = {"drafted": float(len(inferences)), "kept": float(len(kept)), "removed": float(len(inferences) - len(kept)),
                   "abstract_by_model": float(abstract is not None)}  # fmt: skip
        if not verdicts:  # nothing reached the judge: the rules decided everything, and the record says so
            q = Question(id="paper.interpret_rules", type=QuestionType.BOOLEAN,
                         text="Did any statement or abstract pass the deterministic rules and reach the judge?")  # fmt: skip
            verdicts.append(rule_verdict(q, False, COMPONENT))
        sr = stage_result(deps, "interpret", "paper/inferences.jsonl", verdicts, "accept", metrics)
        return {"paper": doc.model_dump(mode="json"), "stage_results": [sr], "trail": ["paper_interpret"]}

    return node


def abstract_prompt(question: str, doc: PaperDocument, claims: dict[str, str], kept: list[Inference]) -> str:
    listed = "\n".join(f"{k}: {v}" for k, v in claims.items())
    readings = "\n".join(f"- {s.text}" for s in kept) or "(none)"
    return (
        f'Write the abstract (at most {ABSTRACT_WORDS} words, one paragraph, plain text) of a review paper titled "{doc.title}" '
        f"on the question: {question}\n\nIt may say only what these verified claims and interpretation statements say, "
        "and should state what the paper finds and what it leaves open. Do not cite sources or claim ids, and do not name "
        f"a source, author or system the claims do not name.\n\nClaims:\n{listed}\n\nInterpretation statements:\n{readings}\n\n"
        "Reply with the abstract only."
    )


INTERPRET_NODES = [("paper_interpret", "interpret", interpret_node)]

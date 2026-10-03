"""Repair what the final audit of a literature section failed: rewrite to what the quote supports, or drop.

The synthesis stage checks every claim once (source resolves, quote is verbatim, the judge path agrees). The final audit
asks the same support question again on the text as written, and can disagree: the common cause is a sentence that
states what its source says and then adds the review's own comparison or caveat under the same citation. This module
takes the audit's `claim_support` failures, asks the generator once to rewrite each failed sentence so it says only
what its quote supports (or to drop it), re-checks each rewrite (quote verbatim, judge confident yes), and puts the
accepted rewrites in the text; a sentence whose rewrite fails is removed. The caller re-runs the audit afterwards.
Nothing here edits the audit: the report decides whether the repaired section passes.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.audit.bibliography import normalise
from vera.audit.literature import cited_sentences, link
from vera.literature import questions, synthesis
from vera.schemas import Question, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
WHY = (
    "the audit found the cited passage does not support this sentence as written: it probably adds a comparison, "
    "interpretation or caveat that no passage states. Keep only what the quote supports"
)


CLAUSE_SPLIT = re.compile(r"[;,]|\b(?:but|and|so|while|whereas)\b")


def dropped_clauses(was: str, now: str) -> list[str]:
    """Clauses of the old sentence that the rewrite no longer states (under half of a clause's content words survive):
    what the repair silently removed, listed so the review can say it (the credal-dro repair lost a caveat)."""

    def words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 4}

    kept = words(now)
    out = []
    for clause in CLAUSE_SPLIT.split(was):
        content = words(clause)
        if len(clause.split()) >= 2 and content and len(content & kept) / len(content) < 0.5:
            out.append(clause.strip())
    return out


def failed_claims(report: dict, text: str, claims: list[dict]) -> list[int]:
    """Indexes (into `claims`) of the claims whose sentence the audit failed on support."""
    sentences = cited_sentences(text)
    normalised = [(normalise(c["claim"]), c) for c in claims]
    out: list[int] = []
    for f in report["findings"]:
        if f["check"] != "claim_support" or f["severity"] != "fail" or not f["claim_ids"]:
            continue
        n = int(f["claim_ids"][0].split(":")[1])
        claim = link(sentences[n][1], normalised) if n < len(sentences) else None
        if claim is not None and claims.index(claim) not in out:
            out.append(claims.index(claim))
    return out


def sentence_in_text(claim: dict) -> str:
    return f"{claim['claim'].rstrip('.')} [{claim['source_key']}]."


def apply(text: str, claims: list[dict], index: int, replacement: dict | None) -> tuple[str, list[dict]]:
    """The text and claims with claim `index` replaced by `replacement` ({"claim", "source_key", ...}) or dropped."""
    old = sentence_in_text(claims[index])
    new = sentence_in_text(replacement) if replacement else ""
    text = text.replace(old, new, 1) if old in text else text
    text = re.sub(r"[ \t]{2,}", " ", re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE))
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    kept = [*claims[:index], *([replacement] if replacement else []), *claims[index + 1 :]]
    return text, kept


def repair(
    question: str,
    text: str,
    claims: list[dict],
    bad: list[int],
    passages: list[dict],
    records: dict[str, dict],
    generate: Callable[[str], str],
    ask: Ask,
) -> tuple[str, list[dict], list[dict]]:
    """One repair pass. Returns (text, claims, log): the log has an entry per failed claim saying what happened."""
    if not bad:
        return text, claims, []
    from vera.loop.stages import _extract_json  # noqa: PLC0415 - shared lenient JSON extraction

    failures = [{"why": WHY, "text": claims[i]["claim"],
                 "claim": {"source_key": claims[i]["source_key"], "quote": claims[i]["quote"]}}
                for i in bad]  # fmt: skip
    reply = _extract_json(generate(synthesis.repair_prompt(question, failures, passages, records)), "[", "]")
    fixes = reply if isinstance(reply, list) else []
    log, replacements = [], {}
    for n, i in enumerate(bad):
        fix = fixes[n] if n < len(fixes) and isinstance(fixes[n], dict) else None
        entry = {"was": claims[i]["claim"], "source_key": claims[i]["source_key"], "outcome": "removed"}
        parsed = synthesis.parse_sentences({"paragraphs": [[fix]]}) if fix else []
        if parsed and parsed[0][0]["claim"]:
            sentence = parsed[0][0]
            claim = {
                "claim": sentence["text"],
                "source_key": sentence["claim"]["source_key"],
                "quote": sentence["claim"]["quote"],
                "quote_check": "pass",
                "locator": "?",
                "verdicts": [],
            }
            status, why = synthesis.check_claim(claim, records, passages)
            passage = synthesis.matched_passage(claim, passages) if status == "pass" else None
            if passage:
                q, material = questions.claim_supported(
                    sentence["text"], passage, records[claim["source_key"]]["title"]
                )
                verdict, confident = ask(q, material)
                if confident and verdict.answer is True:
                    claim["locator"] = passage["locator"]
                    replacements[i] = claim
                    entry |= {
                        "outcome": "rewritten",
                        "now": sentence["text"],
                        "dropped": dropped_clauses(claims[i]["claim"], sentence["text"]),
                    }
                else:
                    entry["why_removed"] = "the rewrite was not confirmed by the judge"
            else:
                entry["why_removed"] = f"the rewrite failed the deterministic check ({why})"
        else:
            entry["why_removed"] = "the generator dropped it or gave no usable rewrite"
        log.append(entry)
    for i in sorted(bad, reverse=True):  # from the back, so earlier indexes stay valid
        text, claims = apply(text, claims, i, replacements.get(i))
    return text, claims, log

# ruff: noqa: E501
"""Measure the checks on the real-case set (Increment 7, SPEC "The real-case set"): Increment 6's checks beside the new ones,
on the same items, against labels made by someone other than the checks' author.

    dev     run on the dev split (P1) against the agent's labels; may be repeated; a question's wording may change only here
    freeze  hash the test split, its labels and the checks' source into data/results/realcase_hash_incr7.json
    test    the one run on the test split (P2, P3); refuses if the freeze is missing or stale, or a test result exists

Per item, as the pipeline runs them (the cheap judge path; an unsure verdict counts as a flag):

- claim (label M or X is faulty): **old** = the quote is verbatim in a passage of its source, the judge says that passage
  supports the claim (`lit.claim_supported`), no editorial connective or back-reference in the sentence, and the judge
  shown the quote alone says it states the claim (`lit.quote_covers_claim`). **new** = old, plus a quote that opens with
  a back-reference, plus `claim.within_quote`. The passage is read from the live run (`runs/<run>/paper/passages.jsonl`),
  not stored in the repo; each row records its hash.
- sentence (label D is faulty; N and F are not): **old** = the Increment 6 screen (a source named by `[Rn]`, a bare key,
  "et al" or an author-year). **new** = the sentence audit (`vera.audit.sentences`) on the sentence as a document made
  before 0.13 records it: rules, then `sentence.no_fact`, then, for a sentence that states a fact, the inference check
  against its section's claims. Only a `fail` is a flag; a `warn` (follows, names no premises) is reported apart.
- inference (label O is faulty): **old** = `vera.audit.inference.check` as Increment 6 ran it. **new** =
  `sentence_checks.check_statement`: the same rules, "X and colleagues", the agreement rule, and the question worded
  clause by clause (tuned on dev only). Synthesis in the sentence audit uses the same new check.

Reported for each type, old and new: the share of faulty items flagged and the share of sound items flagged, each with a
Wilson 95% interval; spend from the run's own ledger. Cap for the whole measurement: $1 (SPEC).

Usage: uv run python scripts/measure_realcase.py dev|freeze|test
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from vera.audit import inference, sentences
from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.literature import anchoring, questions, sentence_checks, synthesis
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / "data" / "realcase"
FREEZE = ROOT / "data" / "results" / "realcase_hash_incr7.json"
RESULTS = ROOT / "data" / "results"
CHECK_FILES = ["vera/literature/sentence_checks.py", "vera/audit/sentences.py", "vera/audit/inference.py",
               "vera/literature/anchoring.py", "vera/literature/synthesis.py", "vera/literature/questions.py",
               "scripts/measure_realcase.py"]  # fmt: skip
CAP_USD = 1.0
MIN_CONFIDENCE = 0.7  # as in the pipeline (LitDeps.min_confidence) and the audits
FAULTY = {"claim": {"M", "X"}, "sentence": {"D"}, "inference": {"O"}}
PAPERS = {"P1": "how-much-useable-information-about-6x3n", "P2": "discuss-the-evolution-of-prompting-guv8",
          "P3": "rlm-vs-clm-3"}  # fmt: skip


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def items(split: str) -> list[dict]:
    rows = [json.loads(ln) for ln in (SET / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["split"] == split]


def labels(split: str) -> dict:
    return json.loads((SET / f"labels_{split}.json").read_text(encoding="utf-8"))


def test_hash() -> str:
    test = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items("test"))
    return hashlib.sha256((test + json.dumps(labels("test")["labels"], sort_keys=True)).encode("utf-8")).hexdigest()


def check_hashes() -> dict[str, str]:
    return {f: sha_bytes((ROOT / f).read_bytes()) for f in CHECK_FILES}


def spent(ledger: Ledger) -> float:
    return sum(r.cost_usd for r in ledger.records())


class Paper:
    """One Increment 6 paper: its claims (from data/paper_demo), titles, and the live run's passages."""

    def __init__(self, pid: str) -> None:
        demo = ROOT / "data" / "paper_demo" / PAPERS[pid]
        doc = json.loads((demo / "paper" / "paper.json").read_text(encoding="utf-8"))
        self.titles = {r["key"]: r["title"] for r in map(json.loads, (demo / "retrieved.jsonl").read_text("utf-8").splitlines()) if r}
        self.claims = {c["id"]: c for c in doc["claims"]}
        live = ROOT / "runs" / PAPERS[pid] / "paper" / "passages.jsonl"
        if not live.exists():
            sys.exit(f"{live} not found: the claim checks need the paper's passages from its live run")
        self.passages = [json.loads(ln) for ln in live.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.records = {k: {"title": t} for k, t in self.titles.items()}

    def audit_claims(self) -> dict[str, dict]:
        return {i: c | {"title": self.titles.get(c["source_key"])} for i, c in self.claims.items()}

    def claim_text(self) -> dict[str, str]:
        return {i: f"{c['claim']} (source: {self.titles.get(c['source_key'], c['source_key'])})" for i, c in self.claims.items()}


def flag_of(v, confident: bool) -> bool:
    return not (confident and v.answer is True)


def claim_row(it: dict, paper: Paper, ask) -> dict:
    c = paper.claims[it["ref"]]
    claim = {"source_key": c["source_key"], "quote": c["quote"]}
    title = paper.titles.get(c["source_key"])
    old, why = [], []
    status, reason = synthesis.check_claim(claim, paper.records, paper.passages)
    passage = synthesis.matched_passage(claim, paper.passages)
    if status == "fail" or passage is None:
        old.append(f"deterministic: {reason or 'no passage'}")
    else:
        q, material = questions.claim_supported(c["claim"], passage, title)
        v, confident = ask(q, material)
        if flag_of(v, confident):
            old.append("lit.claim_supported: " + ("no" if confident else "unsure"))
    marker, dangling = anchoring.marker_problem(c["claim"], c["quote"]), anchoring.dangling_reference(c["claim"])
    if marker:
        old.append(f"marker {marker!r}")
    if dangling:
        old.append(f"back-reference {dangling!r}")
    q, material = anchoring.quote_covers_claim(c["claim"], c["quote"], title)
    v, confident = ask(q, material)
    if flag_of(v, confident):
        old.append("lit.quote_covers_claim: " + ("no" if confident else "unsure"))
    if sentence_checks.leans_on_context(c["quote"]):
        why.append("quote opens with a back-reference")
    q, material = sentence_checks.within_quote(c["claim"], c["quote"], title)
    v, confident = ask(q, material)
    if flag_of(v, confident):
        why.append("claim.within_quote: " + ("no" if confident else "unsure"))
    return {"old": bool(old), "new": bool(old or why), "old_reasons": old, "new_reasons": why,
            "passage_sha256": hashlib.sha256((passage or {}).get("text", "").encode("utf-8")).hexdigest()[:16]}  # fmt: skip


def sentence_row(it: dict, paper: Paper, ask) -> dict:
    text = it["sentence"]
    old = bool(synthesis.STRAY_ATTRIBUTION.search(text) or anchoring.names_a_source_without_a_claim(text))
    entry = {"id": it["sheet_id"], "section": it["section"], "text": text, "kind": "unrecorded", "claims": [], "premises": [],
             "section_claims": list(it["claims"])}  # fmt: skip
    severity, reason, _ = sentences.check_entry(entry, paper.audit_claims(), ask)
    return {"old": old, "new": old or severity == "fail", "old_reasons": ["names a source"] if old else [],
            "new_reasons": [reason] if severity else [], "new_severity": severity}  # fmt: skip


def inference_row(it: dict, paper: Paper, ask) -> dict:
    premises, text = list(it["premises"]), it["statement"]
    reason, _ = inference.check(text, premises, paper.claim_text(), ask)
    source_of = {i: c["source_key"] for i, c in paper.claims.items()}
    new, _ = sentence_checks.check_statement(text, premises, paper.claim_text(), ask, source_of)
    return {"old": reason is not None, "new": new is not None, "old_reasons": [reason] if reason else [],
            "new_reasons": [new] if new else []}  # fmt: skip


ROWS = {"claim": claim_row, "sentence": sentence_row, "inference": inference_row}


def run(split: str) -> dict:
    ledger_path = ROOT / "data" / "ledger" / f"realcase_incr7_{split}.jsonl"
    if split == "test" and ledger_path.exists():
        sys.exit("a test run already exists: the test split is measured once")
    earlier = sum(spent(Ledger(p)) for p in (ROOT / "data" / "ledger").glob("realcase_incr7_*.jsonl"))
    ledger = Ledger(ledger_path, run_id=f"realcase_incr7_{split}")
    budget = Budget(max_usd=CAP_USD - earlier, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="p2.realcase_incr7")
    cache: dict[tuple[str, str], tuple] = {}

    def ask(question, material):
        key = (question.id, question.text, material)
        if key not in cache:  # the old and the new checks share a question on an item: asked once
            (v,) = judge.ask(material, [question])
            cache[key] = (v, v.confidence_source != "none" and v.confidence >= MIN_CONFIDENCE)
        return cache[key]

    lab = labels(split)["labels"]
    papers = {p: Paper(p) for p in sorted({it["paper"] for it in items(split)})}
    rows = []
    for it in items(split):
        row = ROWS[it["type"]](it, papers[it["paper"]], ask)
        label = lab[it["sheet_id"]]
        rows.append({"sheet_id": it["sheet_id"], "item": it["id"], "type": it["type"], "named": it["named"], "label": label,
                     "faulty": label in FAULTY[it["type"]], **row})  # fmt: skip
    return {"rows": rows, "spend_usd": spent(ledger), "ledger": ledger_path.relative_to(ROOT).as_posix()}


def rate(rows: list[dict], key: str) -> dict:
    k, n = sum(r[key] for r in rows), len(rows)
    lo, hi = wilson(k, n) if n else (0.0, 0.0)
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "ci95": [round(lo, 3), round(hi, 3)]}


def summarise(rows: list[dict]) -> dict:
    out = {}
    for t in FAULTY:
        mine = [r for r in rows if r["type"] == t]
        bad, good = [r for r in mine if r["faulty"]], [r for r in mine if not r["faulty"]]
        out[t] = {"n": len(mine), "labels": {lab: sum(r["label"] == lab for r in mine) for lab in sorted({r["label"] for r in mine})},
                  **{f"{which}_{side}": rate(group, which) for which in ("old", "new")
                     for side, group in (("faulty_flagged", bad), ("sound_flagged", good))}}  # fmt: skip
        if t == "sentence":
            out[t]["new_warn"] = sum(1 for r in mine if r.get("new_severity") == "warn")
    return out


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "freeze":
        if FREEZE.exists():
            sys.exit("already frozen: a new freeze needs a new test set")
        if any(RESULTS.glob("realcase_incr7_test.json")):
            sys.exit("a test result exists: the freeze must come before it")
        FREEZE.write_text(json.dumps({"frozen_at": datetime.now(UTC).isoformat(timespec="seconds"), "test_sha256": test_hash(),
                                      "check_sha256": check_hashes()}, indent=1), encoding="utf-8")  # fmt: skip
        print(f"frozen: test and labels {test_hash()[:12]}, check files {len(CHECK_FILES)}")
        return
    if cmd not in ("dev", "test"):
        sys.exit(__doc__)
    if cmd == "test":
        frozen = json.loads(FREEZE.read_text(encoding="utf-8")) if FREEZE.exists() else None
        if frozen is None or frozen["test_sha256"] != test_hash() or frozen["check_sha256"] != check_hashes():
            sys.exit("the freeze is missing or stale (the test split, its labels or a check changed after it): not running")
    out = run(cmd)
    result = {"split": cmd, "run_at": datetime.now(UTC).isoformat(timespec="seconds"), "summary": summarise(out["rows"]),
              "spend_usd": out["spend_usd"], "ledger": out["ledger"], "labelled_by": labels(cmd)["labelled_by"],
              "test_sha256": test_hash(), "check_sha256": check_hashes(), "rows": out["rows"]}  # fmt: skip
    (RESULTS / f"realcase_incr7_{cmd}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["summary"], indent=1), f"\nspend ${out['spend_usd']:.4f}")


if __name__ == "__main__":
    main()

"""Seeded faults, version 2 (Increment 3): subtler faults, more source runs, and a frozen audit.

The Increment 2 set was mostly deterministic faults planted in variants of two source runs, and the audit changed after
its first test run. This set plants faults in documents from at least four source runs (write-ups the loop produced
and the literature sections of the topic runs), including faults the audit may well miss, splits dev/test **by source
run**, and records a hash of the audit's own source code before the test run: a changed audit spends the test set.

Paper faults (a write-up with its results and retrieval log):
  fabricated_citation   unretrieved_citation   altered_reference        (deterministic, as in Increment 2)
  numeric_table         numeric_prose                                    (a number that exists nowhere)
  misattributed_number  a real number from another method or dataset put into a results sentence      (subtle)
  reversed_comparison   a direction word flipped ("lower" for "higher") with the numbers left right    (subtle)
  swapped_method        one idea's name swapped for another's in a results sentence                    (subtle)
Literature faults (a section with its claims, passages and retrieval log):
  unresolved_citation   a `[Rn]` of a source that was never retrieved
  moved_citation        a sentence moved to another retrieved source's key
  fabricated_quote      a claim's quote that is in no passage
  changed_qualifier     a quote with one qualifier changed ("may" for "does")                          (subtle)
  overstated_claim      a claim with an overstatement added, its quote left real                      (subtle)
  swapped_claim_text    two claims' texts exchanged, each keeping its own quote and source             (subtle)

`plant_*` are deterministic given their seed and return None when a document has nowhere to plant the fault.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from vera.audit import seeded
from vera.audit.alignment import idea_methods
from vera.audit.numbers import RESULT_WORDS, direct_values, matches, numbers_in, sentences
from vera.bench.claims import flip_direction

PAPER_FAULTS = ["fabricated_citation", "unretrieved_citation", "altered_reference", "numeric_table", "numeric_prose",
                "misattributed_number", "reversed_comparison", "swapped_method"]  # fmt: skip
LIT_FAULTS = ["unresolved_citation", "moved_citation", "fabricated_quote", "changed_qualifier", "overstated_claim",
              "swapped_claim_text"]  # fmt: skip
SUBTLE = {"misattributed_number", "reversed_comparison", "swapped_method", "changed_qualifier", "overstated_claim",
          "swapped_claim_text"}  # fmt: skip
QUALIFIERS = [("may", "does"), ("can", "must"), ("often", "always"), ("some", "all"), ("might", "will"),
              ("suggests", "proves"), ("could", "does")]  # fmt: skip
FROZEN_FILES = ["vera/audit/__init__.py", "vera/audit/alignment.py", "vera/audit/bibliography.py",
                "vera/audit/citations.py", "vera/audit/literature.py", "vera/audit/numbers.py",
                "vera/literature/questions.py", "vera/literature/synthesis.py", "vera/literature/reading.py",
                "vera/loop/tables.py"]  # fmt: skip


def audit_source_sha256(root: Path) -> str:
    """SHA-256 over the audit's own source (the files above, by path): what 'the audit' means for the freeze."""
    h = hashlib.sha256()
    for rel in sorted(FROZEN_FILES):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


# ── paper faults ─────────────────────────────────────────────────────────────────────────────────────


def _results_sentences(text: str) -> list[str]:
    body = text.partition("## References")[0]
    return [s for sec, s in sentences(text) if RESULT_WORDS.search(s) and s in body and "method" not in sec.lower()]


def plant_paper(kind: str, text: str, results_json: dict, rng: random.Random) -> tuple[str, str, str] | None:
    """(new text, location, description) or None."""
    if kind in seeded.FAULT_TYPES:
        return seeded.plant(kind, text, results_json, rng)
    cand = _results_sentences(text)
    rng.shuffle(cand)
    ideas = [m for m in results_json["results"] if not m.startswith("TreeHFD")]
    if kind == "misattributed_number":
        pool = sorted(direct_values(results_json))
        for s in cand:
            for x in numbers_in(s):
                if "." not in x or len(x.replace(".", "").lstrip("0")) < 3 or not matches(x, set(pool)):
                    continue
                others = [v for v in pool if not matches(x, {v})]
                for v in rng.sample(others, min(len(others), 8)):
                    y = f"{v:.{len(x.split('.')[1])}f}"
                    if y != x and len(y.replace(".", "").lstrip("0")) >= 3:
                        new = text.replace(s, s.replace(x, y, 1), 1)
                        return new, "Results", f"{x} replaced by {y}, a real value elsewhere"
        return None
    if kind == "reversed_comparison":
        for s in cand:
            flipped = flip_direction(s)
            if flipped and re.search(r"lower|higher|better|worse|less|more|faster|slower", s):
                return text.replace(s, flipped, 1), "Results", f"direction word flipped: {s[:60]!r}"
        return None
    if kind == "swapped_method":
        codes = {m.split(":")[0].strip(): m for m in ideas if ":" in m}
        for s in cand:
            named = [c for c in codes if re.search(rf"\b{c}\b", s)]
            others = [c for c in codes if c not in named]
            if named and others and idea_methods(s, results_json["results"]):
                new = re.sub(rf"\b{named[0]}\b", others[0], s, count=1)
                return text.replace(s, new, 1), "Results", f"{named[0]} named as {others[0]}"
        return None
    raise ValueError(f"unknown paper fault {kind!r}")


# ── literature faults ────────────────────────────────────────────────────────────────────────────────

CITED = re.compile(r"([^.\n]*?\S)\s*\[(R\d+)\]\.")


def _cited(text: str) -> list[re.Match]:
    return list(CITED.finditer(text.partition("## References")[0]))


def plant_literature(kind: str, text: str, claims: list[dict], rng: random.Random):
    """(new text, new claims, location, description) or None."""
    matches_ = _cited(text)
    rng.shuffle(matches_)
    if kind in ("unresolved_citation", "moved_citation"):
        keys = sorted({c["source_key"] for c in claims})
        for m in matches_:
            key = m.group(2)
            new = "R999" if kind == "unresolved_citation" else next((k for k in keys if k != key), None)
            if new:
                start = m.start(2)
                return text[:start] + new + text[start + len(key) :], claims, "body", f"[{key}] changed to [{new}]"
        return None
    if kind == "fabricated_quote":
        for i, c in enumerate(claims):
            fake = "the effect is large and consistent across all of the datasets that were examined here"
            new = [*claims[:i], {**c, "quote": fake}, *claims[i + 1 :]]
            return text, new, "claims", f"quote of claim {i} fabricated"
        return None
    if kind == "changed_qualifier":
        idx = list(range(len(claims)))
        rng.shuffle(idx)
        for i in idx:
            for old, new in QUALIFIERS:
                if re.search(rf"\b{old}\b", claims[i]["quote"]):
                    q = re.sub(rf"\b{old}\b", new, claims[i]["quote"], count=1)
                    new_claims = [*claims[:i], {**claims[i], "quote": q}, *claims[i + 1 :]]
                    return text, new_claims, "claims", f"{old!r} -> {new!r}"
        return None
    if kind == "overstated_claim":
        for m in matches_:
            stem = m.group(1).strip()
            claim = next((c for c in claims if stem and (stem in c["claim"] or c["claim"].rstrip(".") in stem)), None)
            if claim and len(stem) > 30:
                over = "It has been conclusively proven that " + stem[0].lower() + stem[1:]
                new_text = text.replace(stem, over, 1)
                new_claims = [{**c, "claim": c["claim"].replace(stem, over, 1)} if c is claim else c for c in claims]
                return new_text, new_claims, "body", f"overstated: {stem[:50]!r}"
        return None
    if kind == "swapped_claim_text":
        pairs = [(a, b) for a in claims for b in claims if a["source_key"] != b["source_key"]]
        rng.shuffle(pairs)
        for a, b in pairs:
            ta, tb = a["claim"].rstrip("."), b["claim"].rstrip(".")
            if ta in text and tb in text and ta != tb and len(ta) > 30 and len(tb) > 30:
                new_text = text.replace(ta, "\x00A", 1).replace(tb, ta, 1).replace("\x00A", tb, 1)
                new_claims = [{**c, "claim": b["claim"]} if c is a else {**c, "claim": a["claim"]} if c is b else c
                              for c in claims]  # fmt: skip
                return new_text, new_claims, "body", f"texts of [{a['source_key']}] and [{b['source_key']}] exchanged"
        return None
    raise ValueError(f"unknown literature fault {kind!r}")


def item_json(rows: list[dict]) -> str:
    return seeded.item_hash(rows)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ── running the audit on an item ─────────────────────────────────────────────────────────────────────

SEEDED_V2 = Path("data") / "seeded_v2"


def item_dir(root: Path, row: dict) -> Path:
    if row["fault_type"] == "control":
        return root / SEEDED_V2 / "base" / row["doc"]
    return root / SEEDED_V2 / "items" / f"{row['doc']}__{row['fault_type']}"


def audit_item(root: Path, row: dict, *, ask, lookup, target: dict | None = None):
    """The audit's run on one item: the write-up audit for a paper, the literature audit for a section."""
    from vera.audit import run_audit, run_literature_audit  # noqa: PLC0415

    base = root / SEEDED_V2 / "base" / row["doc"]
    here = item_dir(root, row)
    retrieved = load_jsonl(base / "retrieved.jsonl")
    if row["kind"] == "paper":
        results = json.loads((base / "results.json").read_text(encoding="utf-8"))
        text = (here / "paper.md").read_text(encoding="utf-8")
        return run_audit(text, results, retrieved, ask=ask, lookup=lookup, paper_id=row["fault_id"],
                         paper_source=f"{here.name}/paper.md", target=target)  # fmt: skip
    text = (here / "literature.md").read_text(encoding="utf-8")
    claims = load_jsonl(here / "claims.jsonl")
    return run_literature_audit(text, claims, load_jsonl(base / "passages.jsonl"), retrieved, ask=ask,
                                paper_id=row["fault_id"], paper_source=f"{here.name}/literature.md")  # fmt: skip

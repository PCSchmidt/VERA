"""The claim-support benchmark (Increment 3): does this passage support this claim? (`lit.claim_supported`)

Items are built from the literature sections the three topic runs produced. Each base pair is a claim that passed the
section's checks (its quote is verbatim in its passage) and the passage it quotes from. From it:

- **supported** (label true): the base pair itself. Its label rests on the quote check and the claim's construction,
  so a drawn sample of them is checked by a person (the label check);
- **other_paper** (false): the claim with a passage of a different paper in the same topic that shares little with it;
- **other_passage** (false): the claim with another passage of the same paper that does not contain its quote and
  shares little with it (a hard negative: right paper, wrong place);
- **reversed** (false): the claim with one direction word flipped ("higher" to "lower"), shown the original passage;
- **altered_number** (false): the claim with a number in it changed, shown the original passage (only when the passage
  holds the number).

A negative whose claim shares many content words with the passage is dropped: it might be supported after all. Items
split by topic (dev: the smallest topic; test: the rest) and the test items' SHA-256 is recorded before any backend sees
them. Items quote other people's papers, so `items.jsonl` is git-ignored; `scripts/build_claim_benchmark.py` rebuilds it
from the runs and the seed.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from vera.literature import questions
from vera.literature.reading import _tokens, quote_in_text
from vera.schemas import BenchmarkItem

SEED = 20261006
MAX_OVERLAP = 0.35  # share of the claim's content words that appear in a negative's passage, at most
PAIRS = [("increase", "decrease"), ("increases", "decreases"), ("increased", "decreased"), ("higher", "lower"),
         ("more", "less"), ("better", "worse"), ("improves", "degrades"), ("improved", "degraded"),
         ("outperform", "underperform"), ("outperforms", "underperforms"), ("stable", "unstable"),
         ("reliable", "unreliable"), ("larger", "smaller"), ("faster", "slower"), ("above", "below"),
         ("agree", "disagree"), ("agrees", "disagrees"), ("improve", "degrade")]  # fmt: skip
FLIPS = {a: b for a, b in PAIRS} | {b: a for a, b in PAIRS}
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\w|\.\d)")


def overlap(claim: str, passage: str) -> float:
    words = set(_tokens(claim))
    return len(words & set(_tokens(passage))) / len(words) if words else 1.0


def flip_direction(claim: str) -> str | None:
    """The claim with its first direction word reversed, or None when it has none."""
    for m in re.finditer(r"[A-Za-z]+", claim):
        word = m.group(0)
        other = FLIPS.get(word.lower())
        if other:
            other = other.capitalize() if word[0].isupper() else other
            return claim[: m.start()] + other + claim[m.end() :]
    return None


def alter_number(claim: str, passage: str, rng: random.Random) -> str | None:
    """The claim with one number (not a year) changed, when the passage holds that number; else None."""
    for m in NUMBER.finditer(claim):
        x = m.group(1)
        if "." not in x and 1900 <= int(x) <= 2100:
            continue
        if x not in passage:
            continue
        value = float(x)
        new = value * rng.choice([0.5, 2.0]) if value else 1.0
        text = f"{new:.{len(x.split('.')[1])}f}" if "." in x else str(max(1, round(new)))
        if text != x:
            return claim[: m.start()] + text + claim[m.end() :]
    return None


# ── base pairs from the topic runs ───────────────────────────────────────────────────────────────────


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def base_pairs(root: Path) -> list[dict]:
    """Every kept claim of every topic run, with its passage, the paper's title and the other passages of the run."""
    manifest = json.loads((root / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    out = []
    for tid in manifest:
        scope = json.loads((root / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run = root / "runs" / scope["run_id"]
        records = {r["key"]: r for r in read_jsonl(run / "retrieved.jsonl")}
        passages = read_jsonl(run / "passages.jsonl")
        for c in read_jsonl(run / "claims.jsonl"):
            mine = [p for p in passages if p["source_key"] == c["source_key"]]
            held = next((p for p in mine if quote_in_text(c["quote"], p["text"])), None)
            if held:
                out.append({"topic": tid, "run": scope["run_id"], "claim": c["claim"], "source_key": c["source_key"],
                            "title": records[c["source_key"]]["title"], "passage": held, "passages": passages,
                            "titles": {k: r["title"] for k, r in records.items()}})  # fmt: skip
    return out


def make_item(n: int, base: dict, claim: str, passage: dict, label: bool, kind: str, split: str,
              extra: dict | None = None) -> BenchmarkItem:  # fmt: skip
    q, material = questions.claim_supported(claim, passage, base["titles"].get(passage["source_key"], base["title"]))
    return BenchmarkItem(
        id=f"claim-{n:04d}", task="claim_support", split=split, question=q, state=material, label=label,
        construction={"kind": kind, "topic": base["topic"], "source_key": base["source_key"],
                      "passage_id": passage["id"], "seed": SEED, **(extra or {})},
        generator="vera.bench.claims 0.1",
    )  # fmt: skip


def build_items(bases: list[dict], dev_topic: str, seed: int = SEED) -> list[BenchmarkItem]:
    rng = random.Random(seed)
    items: list[BenchmarkItem] = []
    n = 0
    for base in bases:
        split = "dev" if base["topic"] == dev_topic else "test"
        claim, own = base["claim"], base["passage"]
        n += 1
        items.append(make_item(n, base, claim, own, True, "supported", split))
        others = [p for p in base["passages"] if p["source_key"] != base["source_key"] and p["kind"] == "fulltext"
                  and overlap(claim, p["text"]) < MAX_OVERLAP]  # fmt: skip
        if others:
            n += 1
            items.append(make_item(n, base, claim, rng.choice(others), False, "other_paper", split))
        same = [p for p in base["passages"] if p["source_key"] == base["source_key"] and p["id"] != own["id"]
                and overlap(claim, p["text"]) < MAX_OVERLAP]  # fmt: skip
        if same:
            n += 1
            items.append(make_item(n, base, claim, rng.choice(same), False, "other_passage", split))
        flipped = flip_direction(claim)
        if flipped:
            n += 1
            items.append(make_item(n, base, flipped, own, False, "reversed", split))
        altered = alter_number(claim, own["text"], rng)
        if altered:
            n += 1
            items.append(make_item(n, base, altered, own, False, "altered_number", split))
    return items


def items_hash(items: list[BenchmarkItem]) -> str:
    lines = sorted(i.model_dump_json() for i in items)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

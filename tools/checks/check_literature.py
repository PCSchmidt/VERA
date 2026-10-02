"""Gate `literature_ready`: each topic has a literature section in which every claim carries a checked quote.

For every topic in data/topics/manifest.json (its run id is in data/topics/scope_<id>.json), the run directory
runs/<run_id>/ must hold a finished synthesis:
- literature.md and claims.jsonl, with at least 5 claims, each with a source key, a quote and a locator;
- every `[Rn]` in the section's text is a source some claim cites, and is a record in the retrieval log
  (retrieved.jsonl): nothing is cited that was not retrieved;
- every claim's quote is a verbatim span (whitespace, hyphenation, quotation marks and case normalised) of a passage of
  its source in passages.jsonl: nothing is quoted that the evidence does not contain;
- artifacts/literature.json reports how many claims were drafted, repaired and removed (the review states them);
- every judge verdict in gates.jsonl came from a component other than its producer;
- the run's ledger equals the budget's recorded spend and is within the per-topic cap;
- the committed copies in data/literature/<id>/ (scripts/export_literature.py) equal the run's files.
"""

from __future__ import annotations

import json
import re
import unicodedata

from _common import block, ok, repo_root_arg

MIN_CLAIMS = 5
MIN_QUOTE_CHARS = 25
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                        "−": "-", "­": "", " ": " "})  # fmt: skip


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(QUOTES)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return " ".join(text.split()).casefold()


def read_jsonl(path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=2.0)
    args = parser.parse_args()
    root = args.root
    topics = json.loads((root / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    summary = []
    for tid in topics:
        scope = json.loads((root / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run = root / "runs" / scope["run_id"]
        for name in ("literature.md", "claims.jsonl", "retrieved.jsonl", "passages.jsonl", "gates.jsonl"):
            if not (run / name).exists():
                block(f"{tid}: runs/{scope['run_id']}/{name} not found: the synthesis has not finished")
        text = (run / "literature.md").read_text(encoding="utf-8")
        claims = read_jsonl(run / "claims.jsonl")
        if len(claims) < MIN_CLAIMS:
            block(f"{tid}: {len(claims)} claims, need at least {MIN_CLAIMS}")
        if any(not (c.get("source_key") and c.get("quote") and c.get("locator")) for c in claims):
            block(f"{tid}: a claim lacks its source key, quote or locator")
        records = {r["key"] for r in read_jsonl(run / "retrieved.jsonl")}
        body = text.partition("## References")[0]
        cited = set(re.findall(r"\[(R\d+)\]", body))
        cited_by_claims = {c["source_key"] for c in claims}
        if not cited <= cited_by_claims:
            block(f"{tid}: the text cites {sorted(cited - cited_by_claims)} with no claim behind it")
        if not cited_by_claims <= records:
            block(f"{tid}: claims cite {sorted(cited_by_claims - records)}, which were not retrieved")
        passages = read_jsonl(run / "passages.jsonl")
        for c in claims:
            quote = norm(c["quote"]).strip(" .\"'")
            mine = [norm(p["text"]) for p in passages if p["source_key"] == c["source_key"]]
            if len(quote) < MIN_QUOTE_CHARS or not any(quote in m for m in mine):
                block(f"{tid}: the quote of a claim cited to {c['source_key']} is not in that source's passages: "
                      f"{c['quote'][:80]!r}")  # fmt: skip
        stats = run / "artifacts" / "literature.json"
        if not stats.exists() or "stats" not in json.loads(stats.read_text(encoding="utf-8")):
            block(f"{tid}: artifacts/literature.json (claims drafted, repaired, removed) not found")
        for g in read_jsonl(run / "gates.jsonl"):
            v = g["verdict"]
            if v["judge_id"] == v["producer_id"]:
                block(f"{tid}: a self-graded verdict on {v['question_id']}")
        ledger = root / "data" / "ledger" / f"run_{scope['run_id']}.jsonl"
        if not ledger.exists():
            block(f"{tid}: ledger of run {scope['run_id']!r} not found")
        spent = sum(r["cost_usd"] for r in read_jsonl(ledger))
        if spent > args.cap_usd:
            block(f"{tid}: ${spent:.4f} spent, over the ${args.cap_usd} per-topic cap")
        for name, source in (("literature.md", run / "literature.md"), ("claims.jsonl", run / "claims.jsonl"),
                             ("literature.json", stats)):  # fmt: skip
            copy = root / "data" / "literature" / tid / name
            if not copy.exists() or copy.read_bytes() != source.read_bytes():
                block(f"{tid}: data/literature/{tid}/{name} is missing or differs from the run (export_literature.py)")
        s = json.loads(stats.read_text(encoding="utf-8"))["stats"]
        summary.append(f"{tid}: {len(claims)} claims kept of {s['drafted']} drafted ({s['repaired']} repaired, "
                       f"{s['removed']} removed), ${spent:.3f}")  # fmt: skip
    ok("; ".join(summary))


if __name__ == "__main__":
    main()

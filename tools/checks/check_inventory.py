"""Gate `inventory_verified`: the corpus inventory is complete and a human spot-checked it.

The inventory is mostly agent-filled, so the agent's work is not accepted on
its own say-so (no self-grading). Two modes:

  check_inventory.py --sample 10 [--seed 42]
      Draw a seeded random sample into data/inventory_spotcheck.csv with an
      empty `verdict` column for a human to fill. Refuses to redraw once any
      verdict exists, so a bad sample can't be quietly replaced.

  check_inventory.py
      Block unless: no blank cells or template rows in the inventory, and every
      sampled row has verdict `correct` or `incorrect`. Prints the error rate.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from _common import block, ok, repo_root_arg

TEMPLATE_IDS = {"example-001"}
# Allowed values: data/README.md is the data dictionary.
ENUMS = {
    "compute_class": {"cpu", "single_gpu", "multi_gpu", "unknown"},
    "candidate_for_p3": {"yes", "no"},
}
URL_FIELDS = ("gen_code_url", "parent_code_url")
SPOTCHECK_FIELDS = ["gen_paper_id", "seed", "verdict", "note"]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def inventory_rows(root: Path) -> list[dict[str, str]]:
    path = root / "data" / "corpus_inventory.csv"
    if not path.exists():
        block("data/corpus_inventory.csv not found")
    fields, rows = read_csv(path)
    if not rows:
        block("data/corpus_inventory.csv has no rows")
    template = [r["gen_paper_id"] for r in rows if r.get("gen_paper_id") in TEMPLATE_IDS
                or "replace this row" in (r.get("notes") or "").lower()]
    if template:
        block(f"template row(s) still present: {', '.join(template)}")
    blanks = [
        f"{r.get('gen_paper_id') or '?'}.{field}"
        for r in rows for field in fields
        if field != "notes" and not (r.get(field) or "").strip()
    ]
    if blanks:
        block(f"{len(blanks)} blank cell(s); write 'unknown' instead: {', '.join(blanks[:8])}")
    bad = [
        f"{r['gen_paper_id']}.{field}={r[field]!r}"
        for r in rows for field, allowed in ENUMS.items()
        if field in r and r[field].strip() not in allowed
    ] + [
        f"{r['gen_paper_id']}.{field}={r[field]!r}"
        for r in rows for field in URL_FIELDS
        if field in r and not (r[field].strip() in {"none", "unknown"} or r[field].strip().startswith(("http://", "https://")))
    ]
    if bad:
        block(f"{len(bad)} value(s) outside data/README.md: {', '.join(bad[:6])}")
    return rows


def check_candidates(rows: list[dict[str, str]]) -> None:
    if "candidate_for_p3" not in (rows[0] if rows else {}):
        return
    yes = [r for r in rows if r["candidate_for_p3"].strip() == "yes"]
    problems = {r.get("parent_id_arxiv_or_doi", r["gen_paper_id"]) for r in yes}
    if not 2 <= len(problems) <= 3:
        block(f"need 2–3 P3 candidate parent problems; found {len(problems)}")
    heavy = [r["gen_paper_id"] for r in yes if r.get("compute_class", "").strip() not in {"cpu", "single_gpu"}]
    if heavy:
        block(f"P3 candidates must be cpu or single_gpu: {', '.join(heavy)}")


def check_hashes(root: Path, rows: list[dict[str, str]]) -> None:
    manifest = root / "data" / "provenance.jsonl"
    if "gen_sha256" not in (rows[0] if rows else {}) or not manifest.exists():
        return
    known = {
        json.loads(line)["sha256"].lower()
        for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    orphan = [r["gen_paper_id"] for r in rows
              if r["gen_sha256"].strip() != "unknown" and r["gen_sha256"].strip().lower() not in known]
    if orphan:
        block(f"gen_sha256 not in data/provenance.jsonl: {', '.join(orphan[:8])}")


def draw_sample(root: Path, n: int, seed: int) -> None:
    rows = inventory_rows(root)
    out = root / "data" / "inventory_spotcheck.csv"
    if out.exists():
        _, existing = read_csv(out)
        if any((r.get("verdict") or "").strip() for r in existing):
            block("data/inventory_spotcheck.csv already has verdicts; refusing to redraw the sample")
    ids = sorted(r["gen_paper_id"] for r in rows)
    sample = random.Random(seed).sample(ids, min(n, len(ids)))
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SPOTCHECK_FIELDS)
        writer.writeheader()
        for paper_id in sample:
            writer.writerow({"gen_paper_id": paper_id, "seed": seed, "verdict": "", "note": ""})
    ok(f"sampled {len(sample)} of {len(ids)} rows (seed {seed}) into {out.relative_to(root).as_posix()}")


def check(root: Path) -> None:
    rows = inventory_rows(root)
    check_candidates(rows)
    check_hashes(root, rows)
    ids = {r["gen_paper_id"] for r in rows}
    out = root / "data" / "inventory_spotcheck.csv"
    if not out.exists():
        block("no spot-check yet: run check_inventory.py --sample 10, then fill the verdicts")
    _, sample = read_csv(out)
    if len(sample) < min(10, len(ids)):
        block(f"spot-check has {len(sample)} row(s); need at least {min(10, len(ids))}")
    unknown = [r["gen_paper_id"] for r in sample if r["gen_paper_id"] not in ids]
    if unknown:
        block(f"spot-check rows not in the inventory: {', '.join(unknown)}")
    pending = [r["gen_paper_id"] for r in sample if (r.get("verdict") or "").strip() not in {"correct", "incorrect"}]
    if pending:
        block(f"{len(pending)} sampled row(s) lack a verdict (correct/incorrect): {', '.join(pending[:8])}")
    wrong = sum(1 for r in sample if r["verdict"].strip() == "incorrect")
    ok(f"inventory complete ({len(rows)} rows); spot-check error rate {wrong}/{len(sample)} "
       f"= {wrong / len(sample):.0%}. Record it in docs/reviews/incr-0.md")


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--sample", type=int, help="draw a spot-check sample of this size")
    parser.add_argument("--seed", type=int, default=None, help="sample seed (default: random, recorded)")
    args = parser.parse_args()
    if args.sample:
        draw_sample(args.root, args.sample, args.seed if args.seed is not None else random.SystemRandom().randrange(10**6))
    else:
        check(args.root)


if __name__ == "__main__":
    main()

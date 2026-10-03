"""Gate `topics_chosen` (and `topics4_chosen`): topics with fixed key-paper lists, recorded before any retrieval.

Requires data/topics/manifest.json (scripts/build_topics_manifest.py) with:
- exactly the three paths of SPEC: one empirical topic with a harness, one empirical without, one non-empirical;
- each topic's file present with the hash recorded (so an edit after the manifest is caught), at least 6 key papers
  with a title, a year and an identifier, and a good-question statement;
- no retrieval output older than the topic's key papers: any data/retrieval/<topic>/retrieved.jsonl record must carry
  a retrieval date no earlier than the day the topic's entry was recorded (the key papers come first; the entry's own
  `recorded_at`, else the manifest's). With `--expect 4` (Increment 4) the manifest holds the three original topics
  plus one fresh one, whose paths need only be among the three.
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg

PATHS = {"empirical_with_harness", "empirical_without_harness", "non_empirical"}
MIN_KEY_PAPERS = 6


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument(
        "--expect", type=int, default=3, help="how many topics the manifest must hold (4 from Increment 4)"
    )
    args = parser.parse_args()
    topics_dir = args.root / "data" / "topics"
    manifest_file = topics_dir / "manifest.json"
    if not manifest_file.exists():
        block("data/topics/manifest.json not found (scripts/build_topics_manifest.py)")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    topics = manifest.get("topics", {})
    if len(topics) != args.expect:
        block(f"{len(topics)} topics in the manifest; SPEC needs exactly {args.expect}")
    found = {t["path"] for t in topics.values()}
    if (found != PATHS) if args.expect == 3 else not found <= PATHS:
        block(
            f"the topics' paths are {sorted(t['path'] for t in topics.values())}; "
            f"need {'exactly ' if args.expect == 3 else 'paths among '}{sorted(PATHS)}"
        )
    for tid, entry in topics.items():
        path = topics_dir / entry["file"]
        if not path.exists():
            block(f"{entry['file']} listed in the manifest is missing")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            block(f"{entry['file']} changed since the manifest was recorded: re-run scripts/build_topics_manifest.py "
                  "(allowed before any retrieval, never after)")  # fmt: skip
        info = json.loads(path.read_text(encoding="utf-8"))
        papers = info.get("key_papers", [])
        if len(papers) < MIN_KEY_PAPERS:
            block(f"{tid}: {len(papers)} key papers, need at least {MIN_KEY_PAPERS}")
        if any(not (p.get("title") and p.get("year") and p.get("id")) for p in papers):
            block(f"{tid}: every key paper needs a title, a year and an identifier")
        if not info.get("good_question", "").strip() or not info.get("text", "").strip():
            block(f"{tid}: the topic text and a good-question statement are required")
        retrieved = args.root / "data" / "retrieval" / tid / "retrieved.jsonl"
        if retrieved.exists():
            day = (entry.get("recorded_at") or manifest["recorded_at"])[:10]  # per topic: its key papers' own date
            early = [ln for ln in retrieved.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and json.loads(ln).get("retrieved", "9999") < day]  # fmt: skip
            if early:
                block(f"{tid}: {len(early)} retrieval records are dated before the manifest ({day})")
    ok(
        f"{args.expect} topics, paths {sorted(PATHS)}, key papers "
        f"{[e['n_key_papers'] for e in topics.values()]}, hashes match"
    )


if __name__ == "__main__":
    main()

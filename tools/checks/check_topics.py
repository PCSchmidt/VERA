"""Gate `topics_chosen`: three topics with fixed key-paper lists, recorded before any retrieval (SPEC "Topics").

Requires data/topics/manifest.json (scripts/build_topics_manifest.py) with:
- exactly the three paths of SPEC: one empirical topic with a harness, one empirical without, one non-empirical;
- each topic's file present with the hash recorded (so an edit after the manifest is caught), at least 6 key papers
  with a title, a year and an identifier, and a good-question statement;
- no retrieval output older than the manifest: any data/retrieval/<topic>/retrieved.jsonl record must carry a
  retrieval date no earlier than the manifest's day (the key papers come first).
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg

PATHS = {"empirical_with_harness", "empirical_without_harness", "non_empirical"}
MIN_KEY_PAPERS = 6


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    topics_dir = args.root / "data" / "topics"
    manifest_file = topics_dir / "manifest.json"
    if not manifest_file.exists():
        block("data/topics/manifest.json not found (scripts/build_topics_manifest.py)")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    topics = manifest.get("topics", {})
    if len(topics) != 3:
        block(f"{len(topics)} topics in the manifest; SPEC needs exactly 3")
    if {t["path"] for t in topics.values()} != PATHS:
        block(f"the topics' paths are {sorted(t['path'] for t in topics.values())}; need exactly {sorted(PATHS)}")
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
            day = manifest["recorded_at"][:10]
            early = [ln for ln in retrieved.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and json.loads(ln).get("retrieved", "9999") < day]  # fmt: skip
            if early:
                block(f"{tid}: {len(early)} retrieval records are dated before the manifest ({day})")
    ok(f"3 topics, paths {sorted(PATHS)}, key papers {[e['n_key_papers'] for e in topics.values()]}, hashes match")


if __name__ == "__main__":
    main()

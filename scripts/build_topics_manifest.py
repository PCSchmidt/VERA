"""Record the approved topics and their key-paper lists with SHA-256 hashes in data/topics/manifest.json.

Run it once the three topic files (data/topics/<id>.json) are final, and before any retrieval for them
(SPEC "No peeking"):
the hash is what proves the key papers were fixed first. Re-running after an edit records the new hash and time, and
the git history shows the change; nothing may be retrieved for a topic before its manifest entry is committed.

Usage: uv run python scripts/build_topics_manifest.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "data" / "topics"


def main() -> None:
    topics = {}
    manifest_file = TOPICS / "manifest.json"
    earlier = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for path in sorted(TOPICS.glob("*.json")):
        if path.name == "manifest.json" or path.name.startswith(("scope_", "parent_")):
            continue
        info = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        before = earlier.get("topics", {}).get(info["id"])
        # a topic whose file is unchanged keeps the time its key papers were fixed; a new or edited one gets now
        recorded = (
            before.get("recorded_at", earlier.get("recorded_at", now)) if before and before["sha256"] == digest else now
        )
        topics[info["id"]] = {
            "file": path.name,
            "sha256": digest,
            "path": info["path"],
            "n_key_papers": len(info["key_papers"]),
            "recorded_at": recorded,
        }
    manifest = {
        "recorded_at": now,
        "note": "Fixed before the first retrieval for these topics (SPEC 'Topics and key papers').",
        "topics": topics,
    }
    (TOPICS / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    for tid, t in topics.items():
        print(f"{tid}: {t['n_key_papers']} key papers, {t['path']}, {t['sha256'][:12]}")


if __name__ == "__main__":
    main()

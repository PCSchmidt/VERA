"""Gate `corpus_fetched`: discovery recorded its source and count, and explains any mismatch.

data/corpus_discovery.json (see data/README.md):
{"source_url", "retrieved", "site_stated_count" (int or null), "discovered_count" (int), "explanation"}
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    path = args.root / "data" / "corpus_discovery.json"
    if not path.exists():
        block("data/corpus_discovery.json not found (written by scripts/discover_corpus.py)")
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        block("data/corpus_discovery.json is not valid JSON")
    for key in ("source_url", "retrieved", "discovered_count"):
        if not rec.get(key) and rec.get(key) != 0:
            block(f"corpus_discovery.json is missing {key}")
    found, stated = rec["discovered_count"], rec.get("site_stated_count")
    if not isinstance(found, int) or found <= 0:
        block(f"discovered_count must be a positive integer, got {found!r}")
    if stated is not None and not isinstance(stated, int):
        block(f"site_stated_count must be an integer or null, got {stated!r}")
    if (stated is None or stated != found) and not str(rec.get("explanation") or "").strip():
        block(f"discovered {found}, site states {stated}: an explanation is required")
    ok(f"discovered {found} generated paper(s); site states {stated}")


if __name__ == "__main__":
    main()

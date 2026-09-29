"""Gate `corpus_fetched` (FND-C-02): every downloaded file has matching provenance; none is committed.

Provenance lives in data/provenance.jsonl, one JSON object per file:
{"path": "data/raw/...", "url": "...", "retrieved": "YYYY-MM-DD", "sha256": "..."}
"""

from __future__ import annotations

import hashlib
import json
import subprocess

from _common import block, ok, repo_root_arg

REQUIRED = ("path", "url", "retrieved", "sha256")


def sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    root = args.root
    raw = root / "data" / "raw"
    files = sorted(p for p in raw.rglob("*") if p.is_file() and p.name != ".gitkeep") if raw.exists() else []
    if not files:
        block("no files under data/raw/; nothing has been downloaded")

    tracked = subprocess.run(
        ["git", "ls-files", "data/raw"], cwd=root, capture_output=True, text=True, check=False
    ).stdout.split()
    tracked = [t for t in tracked if not t.endswith(".gitkeep")]
    if tracked:
        block(f"corpus files are tracked by git (must stay local): {', '.join(tracked[:5])}")

    manifest = root / "data" / "provenance.jsonl"
    if not manifest.exists():
        block("data/provenance.jsonl not found")
    records = {}
    for n, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            block(f"data/provenance.jsonl line {n} is not valid JSON")
        missing = [k for k in REQUIRED if not rec.get(k)]
        if missing:
            block(f"data/provenance.jsonl line {n} is missing {', '.join(missing)}")
        records[rec["path"]] = rec

    problems = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        rec = records.get(rel)
        if rec is None:
            problems.append(f"{rel}: no provenance record")
        elif rec["sha256"].lower() != sha256(path):
            problems.append(f"{rel}: sha256 does not match the file")
    if problems:
        block(f"{len(problems)} file(s) fail provenance: " + "; ".join(problems[:5]))
    ok(f"{len(files)} corpus file(s) have matching provenance; none tracked by git")


if __name__ == "__main__":
    main()

"""Provenance records for downloaded corpus files (FND-C-02).

`data/provenance.jsonl` holds one JSON object per file (data/README.md):
{"path": "data/raw/<...>", "url": "...", "retrieved": "YYYY-MM-DD", "sha256": "<hex>"}
It is the single source for download facts; the inventory links to it by URL.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

MANIFEST = Path("data") / "provenance.jsonl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(root: Path) -> dict[str, dict[str, str]]:
    """Records keyed by repo-relative path, in file order."""
    manifest = root / MANIFEST
    if not manifest.exists():
        return {}
    lines = manifest.read_text(encoding="utf-8").splitlines()
    return {rec["path"]: rec for rec in (json.loads(line) for line in lines if line.strip())}


def is_current(root: Path, file: Path, records: dict[str, dict[str, str]] | None = None) -> bool:
    """True if `file` exists and has a record whose hash matches it."""
    records = load(root) if records is None else records
    rec = records.get(file.relative_to(root).as_posix())
    return file.is_file() and rec is not None and rec["sha256"] == sha256(file)


def record(root: Path, file: Path, url: str, retrieved: dt.date | None = None) -> dict[str, str]:
    """Hash `file` and write its record, replacing any earlier record for the same path."""
    rec = {
        "path": file.relative_to(root).as_posix(),
        "url": url,
        "retrieved": (retrieved or dt.date.today()).isoformat(),
        "sha256": sha256(file),
    }
    records = load(root)
    records[rec["path"]] = rec
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records.values()), encoding="utf-8")
    tmp.replace(manifest)
    return rec

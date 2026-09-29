"""FND-C-02: the provenance writer, exercised on local files only (no network)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from vera import provenance

CHECK = Path(__file__).resolve().parents[1] / "tools" / "checks" / "check_provenance.py"
URL = "https://example.org/p1.pdf"


def pdf(
    root: Path, rel: str = "data/raw/scientisttwo/applications/Time Series_X.pdf", body: bytes = b"%PDF-1.4 a"
) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def test_FND_C_02_record_has_path_url_date_and_matching_hash(tmp_path: Path) -> None:
    file = pdf(tmp_path)
    rec = provenance.record(tmp_path, file, URL, dt.date(2026, 9, 29))
    assert rec == {
        "path": "data/raw/scientisttwo/applications/Time Series_X.pdf",
        "url": URL,
        "retrieved": "2026-09-29",
        "sha256": hashlib.sha256(b"%PDF-1.4 a").hexdigest(),
    }
    lines = (tmp_path / "data" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [rec]


def test_FND_C_02_rerecord_replaces_rather_than_duplicates(tmp_path: Path) -> None:
    file = pdf(tmp_path)
    other = pdf(tmp_path, "data/raw/parents/p.pdf", b"%PDF-1.4 parent")
    provenance.record(tmp_path, file, URL)
    provenance.record(tmp_path, other, "https://example.org/parent.pdf")
    file.write_bytes(b"%PDF-1.4 changed")
    provenance.record(tmp_path, file, URL)
    records = provenance.load(tmp_path)
    assert list(records) == [
        "data/raw/scientisttwo/applications/Time Series_X.pdf",
        "data/raw/parents/p.pdf",
    ]
    assert provenance.is_current(tmp_path, file, records)


def test_FND_C_02_is_current_detects_changed_or_unrecorded_files(tmp_path: Path) -> None:
    file = pdf(tmp_path)
    assert not provenance.is_current(tmp_path, file)
    provenance.record(tmp_path, file, URL)
    assert provenance.is_current(tmp_path, file)
    file.write_bytes(b"%PDF-1.4 tampered")
    assert not provenance.is_current(tmp_path, file)


def test_FND_C_02_writer_output_passes_the_gate_check(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    provenance.record(tmp_path, pdf(tmp_path), URL)
    provenance.record(tmp_path, pdf(tmp_path, "data/raw/parents/p.pdf", b"%PDF-1.4 p"), URL)
    result = subprocess.run(
        [sys.executable, str(CHECK), "--root", str(tmp_path)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

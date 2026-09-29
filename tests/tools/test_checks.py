"""Tests for the Meridian gate checks in tools/checks/ (exit 0 = pass, 2 = block)."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[2] / "tools" / "checks"


def run(check: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKS / check), "--root", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ── spend ceiling ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("line", "code"),
    [
        ("- Monthly spend ceiling: **TBD** (suggest setting one before Increment 1).", 2),
        ("- Monthly spend ceiling: to be decided", 2),
        ("- Monthly spend ceiling: **$50**", 0),
        ("- Monthly spend ceiling: $ 120 per month", 0),
    ],
)
def test_spend_ceiling(tmp_path: Path, line: str, code: int) -> None:
    write(tmp_path, "docs/01-conops.md", f"# ConOps\n\n## 4. Operating envelope\n\n{line}\n")
    assert run("check_spend_ceiling.py", tmp_path).returncode == code


# ── schema version ────────────────────────────────────────────────────────────

DOC03 = "# 03\n\nVersion 0.1 · Draft\n\n## Changelog\n\n- 0.1 — initial draft.\n"


def test_schema_version_blocks_without_package(tmp_path: Path) -> None:
    write(tmp_path, "docs/03-interfaces.md", DOC03)
    assert run("check_schema_version.py", tmp_path).returncode == 2


def test_schema_version_matches(tmp_path: Path) -> None:
    write(tmp_path, "docs/03-interfaces.md", DOC03)
    write(tmp_path, "vera/schemas/version.py", 'SCHEMA_VERSION = "0.1"\n')
    assert run("check_schema_version.py", tmp_path).returncode == 0


def test_schema_version_mismatch_blocks(tmp_path: Path) -> None:
    write(tmp_path, "docs/03-interfaces.md", DOC03)
    write(tmp_path, "vera/schemas/version.py", 'SCHEMA_VERSION = "0.2"\n')
    result = run("check_schema_version.py", tmp_path)
    assert result.returncode == 2
    assert "mismatch" in result.stderr


def test_schema_version_needs_changelog_line(tmp_path: Path) -> None:
    write(tmp_path, "docs/03-interfaces.md", "Version 0.2\n\n## Changelog\n\n- 0.1 — initial draft.\n")
    write(tmp_path, "vera/schemas/version.py", 'SCHEMA_VERSION = "0.2"\n')
    assert run("check_schema_version.py", tmp_path).returncode == 2


# ── traceability ──────────────────────────────────────────────────────────────

REQS = """\
| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| FND-F-01 | ledger | T | 1 |
| FND-C-01 | no vendor SDK | I (lint rule) | 1 |
| FND-C-02 | provenance | T | 0 |
| AUD-P-01 | detection | T | 2–3 |
"""


def trace_repo(root: Path, increment: int, tests: str = "") -> None:
    write(root, "SPEC.md", f"# SPEC — VERA, Increment {increment}\n")
    write(root, "docs/02-requirements.md", REQS)
    if tests:
        write(root, "tests/test_reqs.py", tests)


def test_traceability_blocks_missing_test(tmp_path: Path) -> None:
    trace_repo(tmp_path, 0)
    result = run("check_traceability.py", tmp_path)
    assert result.returncode == 2
    assert "FND-C-02" in result.stderr


def test_traceability_passes_with_named_test(tmp_path: Path) -> None:
    trace_repo(tmp_path, 0, "def test_FND_C_02_hash_matches():\n    pass\n")
    assert run("check_traceability.py", tmp_path).returncode == 0


def test_traceability_ignores_inspection_and_future_increments(tmp_path: Path) -> None:
    # Increment 1: FND-F-01 and FND-C-02 are due (T); FND-C-01 is I; AUD-P-01 starts at 2.
    trace_repo(tmp_path, 1, "def test_FND_C_02_x():\n    pass\n\ndef test_FND_F_01_x():\n    pass\n")
    assert run("check_traceability.py", tmp_path).returncode == 0


def test_traceability_range_uses_first_increment(tmp_path: Path) -> None:
    trace_repo(tmp_path, 2, "def test_FND_C_02_x():\n    pass\n\ndef test_FND_F_01_x():\n    pass\n")
    result = run("check_traceability.py", tmp_path)
    assert result.returncode == 2
    assert "AUD-P-01" in result.stderr


# ── provenance ────────────────────────────────────────────────────────────────

def provenance_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    pdf = root / "data" / "raw" / "scientisttwo" / "p1.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    return pdf


def record(pdf: Path, root: Path, sha: str | None = None) -> str:
    return json.dumps({
        "path": pdf.relative_to(root).as_posix(),
        "url": "https://example.org/p1.pdf",
        "retrieved": "2026-09-29",
        "sha256": sha or hashlib.sha256(pdf.read_bytes()).hexdigest(),
    }) + "\n"


def test_provenance_blocks_when_nothing_downloaded(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert run("check_provenance.py", tmp_path).returncode == 2


def test_provenance_passes_with_matching_hash(tmp_path: Path) -> None:
    pdf = provenance_repo(tmp_path)
    write(tmp_path, "data/provenance.jsonl", record(pdf, tmp_path))
    assert run("check_provenance.py", tmp_path).returncode == 0


def test_provenance_blocks_hash_mismatch(tmp_path: Path) -> None:
    pdf = provenance_repo(tmp_path)
    write(tmp_path, "data/provenance.jsonl", record(pdf, tmp_path, sha="0" * 64))
    result = run("check_provenance.py", tmp_path)
    assert result.returncode == 2
    assert "sha256" in result.stderr


def test_provenance_blocks_file_without_record(tmp_path: Path) -> None:
    provenance_repo(tmp_path)
    write(tmp_path, "data/provenance.jsonl", "")
    assert run("check_provenance.py", tmp_path).returncode == 2


def test_provenance_blocks_committed_corpus(tmp_path: Path) -> None:
    pdf = provenance_repo(tmp_path)
    write(tmp_path, "data/provenance.jsonl", record(pdf, tmp_path))
    subprocess.run(["git", "add", "-f", "data/raw"], cwd=tmp_path, check=True)
    result = run("check_provenance.py", tmp_path)
    assert result.returncode == 2
    assert "tracked by git" in result.stderr


# ── inventory + spot-check ────────────────────────────────────────────────────

FIELDS = ["gen_paper_id", "domain", "method_name", "parent_title", "compute_class", "notes"]


def inventory(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "data" / "corpus_inventory.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def full_rows(n: int) -> list[dict[str, str]]:
    return [
        {"gen_paper_id": f"p{i:03d}", "domain": "DL", "method_name": f"M{i}",
         "parent_title": "unknown", "compute_class": "cpu", "notes": ""}
        for i in range(n)
    ]


def fill_verdicts(root: Path, verdict: str = "correct") -> None:
    path = root / "data" / "inventory_spotcheck.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["verdict"] = verdict
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_inventory_blocks_template_row(tmp_path: Path) -> None:
    rows = full_rows(3)
    rows[0]["gen_paper_id"] = "example-001"
    inventory(tmp_path, rows)
    assert run("check_inventory.py", tmp_path).returncode == 2


def test_inventory_blocks_blank_cells(tmp_path: Path) -> None:
    rows = full_rows(3)
    rows[1]["parent_title"] = ""
    inventory(tmp_path, rows)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "unknown" in result.stderr


def test_inventory_blocks_without_spotcheck(tmp_path: Path) -> None:
    inventory(tmp_path, full_rows(20))
    assert run("check_inventory.py", tmp_path).returncode == 2


def test_inventory_sample_then_verdicts_pass(tmp_path: Path) -> None:
    inventory(tmp_path, full_rows(20))
    assert run("check_inventory.py", tmp_path, "--sample", "10", "--seed", "7").returncode == 0
    assert run("check_inventory.py", tmp_path).returncode == 2  # verdicts still empty
    fill_verdicts(tmp_path)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 0
    assert "0/10" in result.stdout


def test_inventory_sample_is_reproducible(tmp_path: Path) -> None:
    inventory(tmp_path, full_rows(20))
    run("check_inventory.py", tmp_path, "--sample", "10", "--seed", "7")
    first = (tmp_path / "data" / "inventory_spotcheck.csv").read_text(encoding="utf-8")
    run("check_inventory.py", tmp_path, "--sample", "10", "--seed", "7")
    assert (tmp_path / "data" / "inventory_spotcheck.csv").read_text(encoding="utf-8") == first


def test_inventory_refuses_to_redraw_after_verdicts(tmp_path: Path) -> None:
    inventory(tmp_path, full_rows(20))
    run("check_inventory.py", tmp_path, "--sample", "10", "--seed", "7")
    fill_verdicts(tmp_path, "incorrect")
    result = run("check_inventory.py", tmp_path, "--sample", "10", "--seed", "8")
    assert result.returncode == 2
    assert "refusing to redraw" in result.stderr


# ── trade decided ─────────────────────────────────────────────────────────────

def test_trade_open_blocks(tmp_path: Path) -> None:
    write(tmp_path, "docs/04-trade-studies.md",
          "## T3 — PDF parsing (open, decide in Increment 0)\n\n- **Options:** a, b\n")
    assert run("check_trade_decided.py", tmp_path, "T3").returncode == 2


def test_trade_decided_passes(tmp_path: Path) -> None:
    write(
        tmp_path,
        "docs/04-trade-studies.md",
        "## T3 — PDF parsing (decided 2026-10-10)\n\n- **Scores:** GROBID refs 0.95, tables 0.7\n"
        "- **Decision:** GROBID\n- **Reverse if:** tables fail\n\n## T4 — Sandbox (open)\n",
    )
    assert run("check_trade_decided.py", tmp_path, "T3").returncode == 0


def test_trade_decided_needs_scores(tmp_path: Path) -> None:
    write(tmp_path, "docs/04-trade-studies.md",
          "## T3 — PDF parsing (decided)\n\n- **Decision:** GROBID\n- **Reverse if:** tables fail\n")
    result = run("check_trade_decided.py", tmp_path, "T3")
    assert result.returncode == 2
    assert "Scores" in result.stderr


def test_trade_decided_needs_reversal_condition(tmp_path: Path) -> None:
    write(tmp_path, "docs/04-trade-studies.md", "## T3 — PDF parsing (decided)\n\n- **Decision:** GROBID\n")
    assert run("check_trade_decided.py", tmp_path, "T3").returncode == 2


# ── discovery ─────────────────────────────────────────────────────────────────

def discovery(root: Path, **fields: object) -> None:
    rec = {"source_url": "https://example.org", "retrieved": "2026-09-29", "discovered_count": 86,
           "site_stated_count": 86, "explanation": ""}
    rec.update(fields)
    write(root, "data/corpus_discovery.json", json.dumps(rec))


def test_discovery_matching_counts_pass(tmp_path: Path) -> None:
    discovery(tmp_path)
    assert run("check_discovery.py", tmp_path).returncode == 0


def test_discovery_mismatch_needs_explanation(tmp_path: Path) -> None:
    discovery(tmp_path, discovered_count=107)
    assert run("check_discovery.py", tmp_path).returncode == 2
    discovery(tmp_path, discovered_count=107, explanation="site lists all 107 problems; 86 beat SOTA")
    assert run("check_discovery.py", tmp_path).returncode == 0


def test_discovery_unstated_count_needs_explanation(tmp_path: Path) -> None:
    discovery(tmp_path, site_stated_count=None)
    assert run("check_discovery.py", tmp_path).returncode == 2


def test_discovery_missing_file_blocks(tmp_path: Path) -> None:
    assert run("check_discovery.py", tmp_path).returncode == 2


# ── inventory: data dictionary rules ──────────────────────────────────────────

DICT_FIELDS = ["gen_paper_id", "gen_sha256", "gen_code_url", "parent_id_arxiv_or_doi",
               "parent_code_url", "compute_class", "candidate_for_p3", "notes"]


def dict_rows(n: int = 12) -> list[dict[str, str]]:
    rows = [
        {"gen_paper_id": f"p{i:03d}", "gen_sha256": "unknown", "gen_code_url": "none",
         "parent_id_arxiv_or_doi": f"2401.{i:05d}", "parent_code_url": "https://github.com/x/y",
         "compute_class": "cpu", "candidate_for_p3": "no", "notes": ""}
        for i in range(n)
    ]
    rows[0]["candidate_for_p3"] = rows[1]["candidate_for_p3"] = "yes"
    return rows


def dict_inventory(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "data" / "corpus_inventory.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DICT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def spotchecked(root: Path) -> None:
    assert run("check_inventory.py", root, "--sample", "10", "--seed", "1").returncode == 0
    fill_verdicts(root)


def test_inventory_valid_dictionary_passes(tmp_path: Path) -> None:
    dict_inventory(tmp_path, dict_rows())
    spotchecked(tmp_path)
    assert run("check_inventory.py", tmp_path).returncode == 0


@pytest.mark.parametrize(("field", "value"), [
    ("compute_class", "gpu"), ("candidate_for_p3", "maybe"), ("gen_code_url", "n/a"),
])
def test_inventory_rejects_values_outside_dictionary(tmp_path: Path, field: str, value: str) -> None:
    rows = dict_rows()
    rows[5][field] = value
    dict_inventory(tmp_path, rows)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "data/README.md" in result.stderr


def test_inventory_needs_two_to_three_candidate_problems(tmp_path: Path) -> None:
    rows = dict_rows()
    rows[1]["candidate_for_p3"] = "no"
    dict_inventory(tmp_path, rows)
    spotchecked(tmp_path)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "2–3" in result.stderr


def test_inventory_candidates_must_be_small_compute(tmp_path: Path) -> None:
    rows = dict_rows()
    rows[0]["compute_class"] = "multi_gpu"
    dict_inventory(tmp_path, rows)
    spotchecked(tmp_path)
    assert run("check_inventory.py", tmp_path).returncode == 2


def test_inventory_hash_must_match_provenance(tmp_path: Path) -> None:
    rows = dict_rows()
    rows[3]["gen_sha256"] = "ab" * 32
    dict_inventory(tmp_path, rows)
    spotchecked(tmp_path)
    other = {"path": "data/raw/x.pdf", "url": "u", "retrieved": "2026-09-29", "sha256": "cd" * 32}
    write(tmp_path, "data/provenance.jsonl", json.dumps(other) + "\n")
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "provenance" in result.stderr

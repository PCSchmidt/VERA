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
    return (
        json.dumps(
            {
                "path": pdf.relative_to(root).as_posix(),
                "url": "https://example.org/p1.pdf",
                "retrieved": "2026-09-29",
                "sha256": sha or hashlib.sha256(pdf.read_bytes()).hexdigest(),
            }
        )
        + "\n"
    )


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
        {
            "gen_paper_id": f"p{i:03d}",
            "domain": "DL",
            "method_name": f"M{i}",
            "parent_title": "unknown",
            "compute_class": "cpu",
            "notes": "",
        }
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
    write(
        tmp_path,
        "docs/04-trade-studies.md",
        "## T3 — PDF parsing (open, decide in Increment 0)\n\n- **Options:** a, b\n",
    )
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
    write(
        tmp_path,
        "docs/04-trade-studies.md",
        "## T3 — PDF parsing (decided)\n\n- **Decision:** GROBID\n- **Reverse if:** tables fail\n",
    )
    result = run("check_trade_decided.py", tmp_path, "T3")
    assert result.returncode == 2
    assert "Scores" in result.stderr


def test_trade_decided_needs_reversal_condition(tmp_path: Path) -> None:
    write(tmp_path, "docs/04-trade-studies.md", "## T3 — PDF parsing (decided)\n\n- **Decision:** GROBID\n")
    assert run("check_trade_decided.py", tmp_path, "T3").returncode == 2


# ── discovery ─────────────────────────────────────────────────────────────────


def discovery(root: Path, **fields: object) -> None:
    rec = {
        "source_url": "https://example.org",
        "retrieved": "2026-09-29",
        "discovered_count": 86,
        "site_stated_count": 86,
        "explanation": "",
    }
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

DICT_FIELDS = [
    "gen_paper_id",
    "gen_pdf_url",
    "gen_code_url",
    "parent_id_arxiv_or_doi",
    "parent_code_url",
    "compute_class",
    "candidate_for_p3",
    "notes",
]


def pdf_url(i: int) -> str:
    return f"https://scientist-two.github.io/papers/p{i:03d}.pdf"


def dict_rows(n: int = 12) -> list[dict[str, str]]:
    rows = [
        {
            "gen_paper_id": f"p{i:03d}",
            "gen_pdf_url": pdf_url(i),
            "gen_code_url": "none",
            "parent_id_arxiv_or_doi": f"2401.{i:05d}",
            "parent_code_url": "https://github.com/x/y",
            "compute_class": "cpu",
            "candidate_for_p3": "no",
            "notes": "",
        }
        for i in range(n)
    ]
    rows[0]["candidate_for_p3"] = rows[1]["candidate_for_p3"] = "yes"
    return rows


def provenance_for(root: Path, urls: list[str], extra: list[dict[str, str]] | None = None) -> None:
    records = [
        {
            "path": f"data/raw/scientisttwo/{u.rsplit('/', 1)[-1]}",
            "url": u,
            "retrieved": "2026-09-29",
            "sha256": "ab" * 32,
        }
        for u in urls
    ]
    lines = [json.dumps(r) for r in records + (extra or [])]
    write(root, "data/provenance.jsonl", "\n".join(lines) + "\n")


def dict_inventory(root: Path, rows: list[dict[str, str]], provenance: bool = True) -> None:
    path = root / "data" / "corpus_inventory.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DICT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    if provenance:
        provenance_for(root, [r["gen_pdf_url"] for r in rows if r["gen_pdf_url"] != "unknown"])


def spotchecked(root: Path) -> None:
    assert run("check_inventory.py", root, "--sample", "10", "--seed", "1").returncode == 0
    fill_verdicts(root)


def test_inventory_valid_dictionary_passes(tmp_path: Path) -> None:
    dict_inventory(tmp_path, dict_rows())
    spotchecked(tmp_path)
    assert run("check_inventory.py", tmp_path).returncode == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("compute_class", "gpu"),
        ("candidate_for_p3", "maybe"),
        ("gen_code_url", "n/a"),
    ],
)
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


def test_inventory_links_every_pdf_url_to_provenance(tmp_path: Path) -> None:
    rows = dict_rows()
    dict_inventory(tmp_path, rows, provenance=False)
    provenance_for(tmp_path, [r["gen_pdf_url"] for r in rows[1:]])  # row 0's download not recorded
    spotchecked(tmp_path)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "no provenance record: p000" in result.stderr


def test_inventory_blocks_downloads_missing_from_inventory(tmp_path: Path) -> None:
    rows = dict_rows()
    dict_inventory(tmp_path, rows, provenance=False)
    stray = {
        "path": "data/raw/scientisttwo/p999.pdf",
        "url": pdf_url(999),
        "retrieved": "2026-09-29",
        "sha256": "cd" * 32,
    }
    provenance_for(tmp_path, [r["gen_pdf_url"] for r in rows], extra=[stray])
    spotchecked(tmp_path)
    result = run("check_inventory.py", tmp_path)
    assert result.returncode == 2
    assert "missing from the inventory" in result.stderr


def test_inventory_allows_parent_papers_and_unknown_urls(tmp_path: Path) -> None:
    rows = dict_rows()
    rows[4]["gen_pdf_url"] = "unknown"
    dict_inventory(tmp_path, rows, provenance=False)
    parent = {
        "path": "data/raw/parents/2401.00001.pdf",
        "url": "https://arxiv.org/pdf/2401.00001",
        "retrieved": "2026-09-29",
        "sha256": "ef" * 32,
    }
    provenance_for(tmp_path, [r["gen_pdf_url"] for r in rows if r["gen_pdf_url"] != "unknown"], extra=[parent])
    spotchecked(tmp_path)
    assert run("check_inventory.py", tmp_path).returncode == 0


def test_inventory_needs_provenance_file(tmp_path: Path) -> None:
    dict_inventory(tmp_path, dict_rows(), provenance=False)
    spotchecked(tmp_path)
    assert run("check_inventory.py", tmp_path).returncode == 2


# ── benchmark items (benchmark_labeled) ───────────────────────────────────────


def bench(root: Path, verdicts: dict[str, str] | None = None, tamper: bool = False) -> None:
    """A tiny benchmark: 2 items per task, one dev and one test; the three question types."""
    qs = {
        "loop_gate": {"id": "loop.best", "type": "choice", "text": "?", "options": ["A", "B"]},
        "numeric": {"id": "num.count", "type": "score", "text": "?", "scale": [0, 3]},
        "citation": {"id": "cite.contains", "type": "boolean", "text": "?"},
    }
    items = []
    for task, q in qs.items():
        for n, split in enumerate(["dev", "test"], 1):
            items.append({"id": f"{task}-{n}", "task": task, "split": split, "question": q, "state": "s",
                          "label": True, "construction": {"kind": "true"}, "generator": "t"})  # fmt: skip
    items.sort(key=lambda i: i["id"])
    lines = [json.dumps(i, separators=(",", ":")) for i in items]
    write(root, "data/benchmark/items.jsonl", "\n".join(lines) + "\n")
    test = [ln for i, ln in zip(items, lines, strict=True) if i["split"] == "test"]
    digest = hashlib.sha256("\n".join(test).encode()).hexdigest()
    test_ids = [i["id"] for i in items if i["split"] == "test"]
    split = {"test_ids": test_ids, "test_sha256": "0" * 64 if tamper else digest}
    write(root, "data/benchmark/split.json", json.dumps(split))
    rows = ["id,seed,verdict,note"]
    for task in qs:
        for n in (1, 2, 1):  # three checks per task (an item may be drawn twice across samples)
            v = (verdicts or {}).get(f"{task}-{n}", "correct")
            rows.append(f"{task}-{n},42,{v},{'relabelled; generator re-checked' if v == 'fixed' else ''}")
    write(root, "data/benchmark/label_check.csv", "\n".join(rows) + "\n")


def test_JDG_F_06_benchmark_check_passes_when_built_split_and_checked(tmp_path: Path) -> None:
    bench(tmp_path)
    result = run("check_benchmark_items.py", tmp_path)
    assert result.returncode == 0, result.stderr


def test_JDG_F_06_benchmark_check_blocks_a_changed_test_split(tmp_path: Path) -> None:
    bench(tmp_path, tamper=True)
    result = run("check_benchmark_items.py", tmp_path)
    assert result.returncode == 2 and "hash" in result.stderr


@pytest.mark.parametrize(
    ("verdicts", "message"),
    [
        ({"numeric-1": "incorrect"}, "not yet fixed"),
        ({"citation-2": ""}, "fewer than 3"),
        ({"loop_gate-1": "maybe"}, "not one of"),
    ],
)
def test_JDG_F_06_benchmark_check_blocks_unresolved_or_missing_label_checks(
    tmp_path: Path, verdicts: dict[str, str], message: str
) -> None:
    bench(tmp_path, verdicts)
    result = run("check_benchmark_items.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


def test_JDG_F_06_benchmark_check_accepts_fixed_labels_with_a_note(tmp_path: Path) -> None:
    bench(tmp_path, {"numeric-1": "fixed"})
    assert run("check_benchmark_items.py", tmp_path).returncode == 0


# ── ledger (backends_live) ────────────────────────────────────────────────────


def ledger_line(backend: str, cost: float = 0.001, error: str | None = None, **over) -> str:
    rec = {"trace_id": "t1", "run_id": "smoke", "component": "p2.smoke", "backend": backend, "model": "m",
           "input_tokens": None if error else 100, "output_tokens": None if error else 10,
           "cost_usd": 0.0 if error else cost, "latency_ms": 300, "timestamp": "2026-09-30T00:00:00Z",
           "error": error}  # fmt: skip
    return json.dumps(rec | over)


def test_FND_F_01_ledger_check_passes_two_backends_with_a_failed_call(tmp_path: Path) -> None:
    lines = [ledger_line("cheap"), ledger_line("ref"), ledger_line("ref", error="HTTP 400: nope")]
    write(tmp_path, "data/ledger/smoke.jsonl", "\n".join(lines) + "\n")
    result = run("check_ledger.py", tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([ledger_line("cheap"), ledger_line("cheap")], "need 2"),
        ([ledger_line("cheap"), ledger_line("ref", error="down")], "need 2"),
        ([ledger_line("cheap"), ledger_line("ref", cost=0.0)], "paid backend"),
        ([ledger_line("cheap"), ledger_line("ref", input_tokens=None)], "not a count"),
        ([ledger_line("cheap"), json.dumps({"backend": "ref"})], "missing fields"),
        ([ledger_line("cheap", cost=0.6), ledger_line("ref", cost=0.5)], "exceeds"),
    ],
)
def test_FND_F_01_ledger_check_blocks(tmp_path: Path, lines: list[str], message: str) -> None:
    write(tmp_path, "data/ledger/smoke.jsonl", "\n".join(lines) + "\n")
    result = run("check_ledger.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


def test_FND_F_01_ledger_check_allows_named_free_backends(tmp_path: Path) -> None:
    write(tmp_path, "data/ledger/smoke.jsonl", ledger_line("cheap") + "\n" + ledger_line("local", cost=0.0) + "\n")
    assert run("check_ledger.py", tmp_path, "--free", "local").returncode == 0


# ── benchmark results (benchmark_run) ─────────────────────────────────────────


def results_fixture(root: Path, *, ledger_cost: float = 0.5, drop_threshold: bool = False, tamper: bool = False,
                    drop_metric: bool = False) -> None:  # fmt: skip
    bench(root)  # items, split and label checks from the benchmark_labeled fixture
    split = json.loads((root / "data/benchmark/split.json").read_text(encoding="utf-8"))
    metrics = {"agreement_label": 0.9, "agreement_reference": 0.95, "ece": 0.05, "flip_rate": 0.02,
               "cost_per_item_usd": 0.001, "latency_p50_ms": 500, "latency_p95_ms": 900, "malformed_rate": 0.0,
               "items": 3, "repeats": 10}  # fmt: skip
    thresholds = [round(0.05 * k, 2) for k in range(21)]
    if drop_threshold:
        thresholds.pop()
    row = {"agreement_label": 0.9, "agreement_reference": 0.95, "escalation_rate": 0.1, "cost_per_item_usd": 0.001,
           "latency_p50_ms": 500, "latency_p95_ms": 900}  # fmt: skip
    cheap = dict(metrics)
    if drop_metric:
        del cheap["ece"]
    results = {"reference": "ref", "test_sha256": "0" * 64 if tamper else split["test_sha256"],
               "backends": {"ref": metrics, "cheap": cheap},
               "sweep": {"cheap": [row | {"threshold": t} for t in thresholds]}}  # fmt: skip
    write(root, "data/benchmark/results.json", json.dumps(results))
    write(root, "data/ledger/bench_ref.jsonl", json.dumps({"cost_usd": ledger_cost}) + "\n")
    write(root, "data/ledger/bench_cheap.jsonl", json.dumps({"cost_usd": 0.01}) + "\n")


def test_JDG_F_06_results_check_passes_a_complete_run(tmp_path: Path) -> None:
    results_fixture(tmp_path)
    result = run("check_benchmark_results.py", tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"ledger_cost": 8.5}, "> $8.00"),
        ({"drop_threshold": True}, "does not cover thresholds"),
        ({"tamper": True}, "different test split"),
        ({"drop_metric": True}, "missing metrics"),
    ],
)
def test_JDG_F_06_results_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    results_fixture(tmp_path, **kwargs)
    result = run("check_benchmark_results.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


# ── dogfood overhead per gate day ─────────────────────────────────────────────


def dogfood_fixture(root: Path, overhead: list[tuple[str, float]]) -> None:
    events = [
        {"timestamp": "2026-10-01T15:13:24Z", "event_type": "gate_passed", "gate": "incr1_review"},
        {"timestamp": "2026-10-01T16:00:00Z", "event_type": "gate_passed", "gate": "run_core_ready"},
        {"timestamp": "2026-10-02T10:00:00Z", "event_type": "gate_passed", "gate": "loop_run"},
    ]
    write(root, ".meridian/telemetry.jsonl", "\n".join(json.dumps(e) for e in events) + "\n")
    rows = [{"type": "overhead", "recorded_at": at, "hours": h} for at, h in overhead]
    write(root, ".meridian/dogfood.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n")


def test_dogfood_check_passes_with_an_entry_for_each_gate_day(tmp_path: Path) -> None:
    dogfood_fixture(tmp_path, [("2026-10-01T17:00:00Z", 1.0), ("2026-10-02T12:00:00Z", 2.0)])
    result = run("check_dogfood.py", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "2026-10-02: 1 gates, 2 h" in result.stdout


def test_dogfood_check_opens_the_increment_at_the_latest_review_gate(tmp_path: Path) -> None:
    dogfood_fixture(tmp_path, [("2026-10-02T12:00:00Z", 2.0)])
    events = [json.loads(ln) for ln in (tmp_path / ".meridian/telemetry.jsonl").read_text().splitlines()]
    events += [
        {"timestamp": "2026-10-02T11:00:00Z", "event_type": "gate_passed", "gate": "incr2_review"},
        {"timestamp": "2026-10-03T09:00:00Z", "event_type": "gate_passed", "gate": "incr3_scoped"},
    ]
    write(tmp_path, ".meridian/telemetry.jsonl", "\n".join(json.dumps(e) for e in events) + "\n")
    result = run("check_dogfood.py", tmp_path)  # since incr2_review: only 10-03 counts, and it has no entry
    assert result.returncode == 2 and "2026-10-03" in result.stderr and "2026-10-01" not in result.stderr
    entry = {"type": "overhead", "recorded_at": "2026-10-03T12:00:00Z", "hours": 1.0}
    with (tmp_path / ".meridian/dogfood.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    assert run("check_dogfood.py", tmp_path).returncode == 0


def test_dogfood_check_blocks_without_any_review_gate(tmp_path: Path) -> None:
    event = {"timestamp": "2026-10-01T10:00:00Z", "event_type": "gate_passed", "gate": "confirmed"}
    write(tmp_path, ".meridian/telemetry.jsonl", json.dumps(event) + "\n")
    assert run("check_dogfood.py", tmp_path).returncode == 2


def test_dogfood_check_blocks_a_gate_day_without_an_entry(tmp_path: Path) -> None:
    dogfood_fixture(tmp_path, [("2026-10-02T12:00:00Z", 2.0)])
    result = run("check_dogfood.py", tmp_path)
    assert result.returncode == 2 and "2026-10-01" in result.stderr


def test_dogfood_check_ignores_zero_hour_entries_and_entries_from_before_the_increment(tmp_path: Path) -> None:
    dogfood_fixture(tmp_path, [("2026-10-01T17:00:00Z", 0), ("2026-10-02T12:00:00Z", 1.0)])
    assert run("check_dogfood.py", tmp_path).returncode == 2  # a zero-hour entry covers nothing
    # an entry at 15:00 on 10-01 is before incr1_review passed (15:13): it does not cover 10-01
    dogfood_fixture(tmp_path, [("2026-10-01T15:00:00Z", 1.5), ("2026-10-02T12:00:00Z", 1.0)])
    result = run("check_dogfood.py", tmp_path)
    assert (
        result.returncode == 2 and "2026-10-01" in result.stderr and "1 earlier entries do not count" in result.stderr
    )
    dogfood_fixture(
        tmp_path, [("2026-10-01T15:00:00Z", 1.5), ("2026-10-01T17:00:00Z", 1.0), ("2026-10-02T12:00:00Z", 1.0)]
    )
    result = run("check_dogfood.py", tmp_path)
    assert result.returncode == 0 and "1 entries recorded before the increment opened were not counted" in result.stdout


# ── topics_chosen ─────────────────────────────────────────────────────────────

TOPIC_PATHS = ("empirical_with_harness", "empirical_without_harness", "non_empirical")


def topics_fixture(root: Path, *, n_papers: int = 6, paths: tuple = TOPIC_PATHS, tamper: bool = False,
                   retrieved_on: str | None = None) -> None:  # fmt: skip
    entries = {}
    for i, path in enumerate(paths):
        tid = f"topic{i}"
        info = {
            "id": tid,
            "text": "t",
            "path": path,
            "good_question": "q",
            "key_papers": [{"title": f"p{k}", "year": 2020, "id": f"arXiv:2001.{k:05d}"} for k in range(n_papers)],
        }
        body = json.dumps(info)
        write(root, f"data/topics/{tid}.json", body)
        entries[tid] = {"file": f"{tid}.json", "sha256": hashlib.sha256(body.encode()).hexdigest(), "path": path,
                        "n_key_papers": n_papers}  # fmt: skip
        if retrieved_on:
            record = json.dumps({"key": "R1", "retrieved": retrieved_on})
            write(root, f"data/retrieval/{tid}/retrieved.jsonl", record + "\n")
    manifest = {"recorded_at": "2026-10-03T10:00:00Z", "topics": entries}
    write(root, "data/topics/manifest.json", json.dumps(manifest))
    if tamper:
        write(root, "data/topics/topic0.json", json.dumps({"id": "topic0", "edited": True}))


def test_topics_check_passes_three_hashed_topics(tmp_path: Path) -> None:
    topics_fixture(tmp_path)
    result = run("check_topics.py", tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_papers": 5}, "need at least 6"),
        ({"paths": ("empirical_with_harness", "empirical_with_harness", "non_empirical")}, "need exactly"),
        ({"tamper": True}, "changed since the manifest"),
        ({"retrieved_on": "2026-10-01"}, "before the manifest"),
    ],
)
def test_topics_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    topics_fixture(tmp_path, **kwargs)
    result = run("check_topics.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


def test_topics_check_allows_retrieval_after_the_manifest(tmp_path: Path) -> None:
    topics_fixture(tmp_path, retrieved_on="2026-10-04")
    assert run("check_topics.py", tmp_path).returncode == 0


# ── scoping_ready ─────────────────────────────────────────────────────────────


def scoping_fixture(root: Path, *, status: str = "confirmed", scope_cost: float = 0.02, stray: bool = False,
                    late_stray: bool = False, by: str | None = "Chris") -> None:  # fmt: skip
    topics_fixture(root)
    for i in range(3):
        tid = f"topic{i}"
        scoped = {"status": status, "confirmed_by": by, "confirmed_at": "2026-10-03T10:00:00Z",
                  "run_id": f"scope-{tid}"}  # fmt: skip
        write(root, f"data/topics/scope_{tid}.json", json.dumps(scoped))
        rows = [("p3.scope", scope_cost, "2026-10-03T09:00:00Z"), ("p2.judge", 0.0001, "2026-10-03T09:00:05Z")]
        if stray:
            rows.append(("p3.retrieve", 0.01, "2026-10-03T09:30:00Z"))
        if late_stray:
            rows.append(("p3.retrieve", 1.0, "2026-10-03T11:00:00Z"))  # after the confirmation: allowed
        lines = [json.dumps({"component": c, "cost_usd": cost, "timestamp": ts}) for c, cost, ts in rows]
        write(root, f"data/ledger/run_scope-{tid}.jsonl", "\n".join(lines) + "\n")


def test_scoping_check_passes_confirmed_topics_within_the_cap(tmp_path: Path) -> None:
    scoping_fixture(tmp_path, status="edited", late_stray=True)
    result = run("check_scoping.py", tmp_path)
    assert result.returncode == 0 and "3 of 3 edited" in result.stdout, result.stderr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"status": "proposed"}, "not confirmed"),
        ({"by": None}, "not confirmed"),
        ({"scope_cost": 0.5}, "over the $0.25 cap"),
        ({"stray": True}, "other than scoping"),
    ],
)
def test_scoping_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    scoping_fixture(tmp_path, **kwargs)
    result = run("check_scoping.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


# ── retrieval_ready ───────────────────────────────────────────────────────────


def retrieval_fixture(root: Path, *, per_topic: int = 15, verdict: str = "yes", drop_field: bool = False,
                      cost: float = 0.05, model_answer: bool = True, confident: bool = True) -> None:  # fmt: skip
    scoping_fixture(root)
    rows, key = ["topic,key,title,year,abstract,your_verdict"], {}
    for i in range(3):
        tid = f"topic{i}"
        record = {"key": "R1", "title": "t", "id": "arXiv:1", "source": "arxiv", "query": "q", "rank": 1,
                  "retrieved": "2026-10-04"}  # fmt: skip
        if drop_field:
            del record["query"]
        write(root, f"data/retrieval/{tid}/retrieved.jsonl", json.dumps(record) + "\n")
        write(
            root,
            f"data/ledger/run_scope-{tid}.jsonl",
            json.dumps({"component": "p3.scope", "cost_usd": cost, "timestamp": "2026-10-03T09:00:00Z"}) + "\n",
        )
        for k in range(per_topic):
            rows.append(f"{tid},R{k},title,2020,abstract,{verdict}")
            key[f"{tid}:R{k}"] = {"answer": model_answer, "confident": confident}
    write(root, "data/retrieval/relevance_check.csv", "\n".join(rows) + "\n")
    write(root, "data/retrieval/relevance_key.json", json.dumps(key))
    write(root, "docs/results/retrieval_recall.md", "\n".join(f"## topic{i}" for i in range(3)))


def test_retrieval_check_passes_and_reports_agreement_with_an_interval(tmp_path: Path) -> None:
    retrieval_fixture(tmp_path)
    result = run("check_retrieval.py", tmp_path)
    assert result.returncode == 0 and "45 of 45" in result.stdout and "95% CI" in result.stdout, result.stderr


def test_retrieval_check_reports_low_agreement_without_blocking(tmp_path: Path) -> None:
    retrieval_fixture(tmp_path, model_answer=False)  # the screen says no to everything the user says yes to
    result = run("check_retrieval.py", tmp_path)
    assert result.returncode == 0 and "0 of 45" in result.stdout


def test_retrieval_check_sets_unsure_verdicts_aside(tmp_path: Path) -> None:
    retrieval_fixture(tmp_path, confident=False)
    result = run("check_retrieval.py", tmp_path)
    assert result.returncode == 0 and "0 of 0" in result.stdout and "45 unsure" in result.stdout


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"per_topic": 14}, "need 15"),
        ({"verdict": ""}, "must be yes or no"),
        ({"drop_field": True}, "missing a field"),
        ({"cost": 3.0}, "over the $2.0 per-topic cap"),
    ],
)
def test_retrieval_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    retrieval_fixture(tmp_path, **kwargs)
    result = run("check_retrieval.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


# ── literature_ready ──────────────────────────────────────────────────────────

QUOTE = "the decomposition becomes unstable across bootstrap refits when correlation exceeds"


def literature_fixture(root: Path, *, n_claims: int = 5, bad_quote: bool = False, stray_cite: bool = False,
                       unretrieved: bool = False, self_graded: bool = False, cost: float = 0.1,
                       drift: bool = False, no_stats: bool = False) -> None:  # fmt: skip
    scoping_fixture(root)
    for i in range(3):
        tid = f"topic{i}"
        run = f"scope-{tid}"
        base = f"runs/{run}"
        claims = [
            {
                "claim": f"claim {k}",
                "source_key": "R9" if unretrieved else "R1",
                "quote": "a quote that is nowhere in any passage at all" if bad_quote else QUOTE,
                "locator": "sec. Results, para 4",
                "quote_check": "pass",
            }
            for k in range(n_claims)
        ]
        text = "Intro [R1].\n\n## References\n\n[R1] A. Author. Title. 2020. arXiv:1. https://x\n"
        if unretrieved:
            text = text.replace("Intro [R1]", "Intro [R9]")
        if stray_cite:
            text = text.replace("Intro [R1].", "Intro [R1] and [R2].")
        write(root, f"{base}/literature.md", text)
        write(root, f"{base}/claims.jsonl", "\n".join(json.dumps(c) for c in claims) + "\n")
        write(root, f"{base}/retrieved.jsonl", json.dumps({"key": "R1"}) + "\n" + json.dumps({"key": "R2"}) + "\n")
        passage = {"source_key": "R1", "id": "R1-P1", "text": f"In our experiments {QUOTE} 0.9, while others hold."}
        write(root, f"{base}/passages.jsonl", json.dumps(passage) + "\n")
        verdict = {
            "judge_id": "p2.judge",
            "producer_id": "p2.judge" if self_graded else "p3.synthesize",
            "question_id": "lit.claim_supported",
        }
        write(root, f"{base}/gates.jsonl", json.dumps({"verdict": verdict}) + "\n")
        stats = {"stats": {"drafted": n_claims, "repaired": 0, "removed": 0}}
        if not no_stats:
            write(root, f"{base}/artifacts/literature.json", json.dumps(stats))
            lines = "\n".join(json.dumps(c) for c in claims) + "\n"
            for name, content in (("literature.md", text), ("claims.jsonl", lines),
                                  ("literature.json", json.dumps(stats))):  # fmt: skip
                extra = "x" if drift and name == "literature.md" else ""
                write(root, f"data/literature/{tid}/{name}", content + extra)
        write(
            root,
            f"data/ledger/run_{run}.jsonl",
            json.dumps({"component": "p3.scope", "cost_usd": cost, "timestamp": "2026-10-03T09:00:00Z"}) + "\n",
        )


def test_literature_check_passes_a_verified_section_per_topic(tmp_path: Path) -> None:
    literature_fixture(tmp_path)
    result = run("check_literature.py", tmp_path)
    assert result.returncode == 0 and "5 claims kept of 5 drafted" in result.stdout, result.stderr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_claims": 4}, "need at least 5"),
        ({"bad_quote": True}, "not in that source's passages"),
        ({"stray_cite": True}, "with no claim behind it"),
        ({"unretrieved": True}, "which were not retrieved"),
        ({"self_graded": True}, "self-graded verdict"),
        ({"cost": 3.0}, "over the $2.0 per-topic cap"),
        ({"drift": True}, "differs from the run"),
        ({"no_stats": True}, "not found"),
    ],
)
def test_literature_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    literature_fixture(tmp_path, **kwargs)
    result = run("check_literature.py", tmp_path)
    assert result.returncode == 2 and message in result.stderr


# ── audit3_ready ──────────────────────────────────────────────────────────────


def seeded_fixture(root: Path, *, tamper: bool = False, stale_audit: bool = False, n_faults: int = 24) -> None:
    import csv as csv_mod  # noqa: PLC0415
    import hashlib  # noqa: PLC0415

    sys.path.insert(0, str(CHECKS))
    import check_seeded_v2 as c  # noqa: PLC0415

    for rel in c.FROZEN_FILES:
        write(root, rel, f"# {rel}\n")
    types = ["fabricated_citation", "numeric_table", "reversed_comparison", "swapped_method", "altered_reference",
             "numeric_prose"]  # fmt: skip
    docs = ["d1", "d2", "d3", "d4"]
    rows = [{"fault_id": f"{d}:control", "doc": d, "kind": "paper", "fault_type": "control", "location": "",
             "description": "", "subtle": "", "split": "test"} for d in docs]  # fmt: skip
    rows += [{"fault_id": f"{docs[i % 4]}:{types[i % 6]}{i}", "doc": docs[i % 4], "kind": "paper",
              "fault_type": types[i % 6], "location": "", "description": "", "subtle": "", "split": "test"}
             for i in range(n_faults)]  # fmt: skip
    rows += [{"fault_id": "d5:control", "doc": "d5", "kind": "paper", "fault_type": "control", "location": "",
              "description": "", "subtle": "", "split": "test"}] * 2  # fmt: skip
    seen = set()
    for r in rows:
        if r["fault_type"] == "control":
            write(root, f"data/seeded_v2/base/{r['doc']}/paper.md", f"control {r['doc']}")
        else:
            write(root, f"data/seeded_v2/items/{r['doc']}__{r['fault_type']}/paper.md", f"fault {r['fault_id']}")
        seen.add(r["fault_id"])
    # items sharing doc and fault_type collide in the hash only through identical files: fine
    cols = list(rows[0])
    path = root / "data/seeded_v2/manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv_mod.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    frozen = c.source_hash(root)
    test_sha = c.test_hash(root, rows)
    if tamper:
        write(root, "data/seeded_v2/items/d1__fabricated_citation/paper.md", "edited after the split")
    if stale_audit:
        write(root, "vera/audit/numbers.py", "# changed after the freeze\n")
    split = {"test_sha256": test_sha, "frozen_audit_sha256": frozen}
    write(root, "data/seeded_v2/split.json", json.dumps(split))
    by_type = {t: {"red": {"k": 1, "n": 1, "ci95": [0.2, 1.0]}, "flagged": {"k": 1, "n": 1}} for t in types}
    summary = {"planted": n_faults, "controls": len(rows) - n_faults, "red": {"k": 20, "n": n_faults},
               "flagged": {"k": 22, "n": n_faults}, "false_fails": 0, "spent_usd": 0.02, "audit_sha256": frozen,
               "by_type": by_type}  # fmt: skip
    write(root, "data/seeded_v2/results_test.json", json.dumps({"summary": summary}))
    del hashlib


def test_seeded_check_passes_a_frozen_tested_set(tmp_path: Path) -> None:
    seeded_fixture(tmp_path)
    result = run("check_seeded_v2.py", tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"tamper": True}, "hash differs"), ({"stale_audit": True}, "changed after it was frozen"),
     ({"n_faults": 12}, "needs at least 24")],
)  # fmt: skip
def test_seeded_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    seeded_fixture(tmp_path, **kwargs)
    result = run("check_seeded_v2.py", tmp_path)
    assert result.returncode == 2
    assert message in result.stderr


# ── topic_runs ────────────────────────────────────────────────────────────────

TOPICS = {"t-a": True, "t-b": True, "t-c": False}  # topic id -> empirical


def ledger_file(root: Path, run_id: str, cost: float) -> None:
    write(root, f"data/ledger/run_{run_id}.jsonl", json.dumps({"cost_usd": cost}) + "\n")


def topic_runs_fixture(root: Path, *, incomplete: str | None = None, self_graded: bool = False, no_audit: bool = False,
                       no_reading: bool = False, no_loop: bool = False, drop_stage: str | None = None,
                       ledger_drift: bool = False, over_cap: bool = False) -> None:  # fmt: skip
    write(root, "data/topics/manifest.json", json.dumps({"topics": {t: {} for t in TOPICS}}))
    costs: dict = {}
    for tid, empirical in TOPICS.items():
        run_id = f"scope-{tid}-1"
        write(root, f"data/topics/scope_{tid}.json", json.dumps({"run_id": run_id, "empirical": empirical}))
        stages = ["scope", "retrieve", "read", "synthesize"] + (["parent"] if empirical else [])
        stages = [s for s in stages if s != drop_stage]

        def gate(s: str) -> dict:
            judge = f"p3.{s}" if self_graded else "p2.judge"
            return {"question": "q", "answer": True, "confidence": 0.9, "judge": judge, "producer": f"p3.{s}"}

        rec = {"run_id": run_id, "topic_id": tid, "completed": incomplete != tid, "stop_reason": "x",
               "stages": [{"stage": s, "decision": "accept", "producer": f"p3.{s}", "gates": [gate(s)]}
                          for s in stages],
               "ledger_total_usd": (3.0 if over_cap else 0.5) + (1.0 if ledger_drift else 0.0),
               "audit": None if no_audit else {"overall": "amber"}}  # fmt: skip
        write(root, f"data/results/topic_run_{run_id}.json", json.dumps(rec))
        ledger_file(root, run_id, 3.0 if over_cap else 0.5)
        picked = "https://github.com/a/b" if empirical else None
        review = {"right": True, "by": "Chris", "at": "2026-10-03T10:00:00Z"}
        parent = {
            "picked": picked,
            "none_fits_reason": None if picked else "not empirical",
            "user_review": None if (no_reading or not empirical) else review,
        }
        write(root, f"data/topics/parent_{tid}.json", json.dumps(parent))
        costs[tid] = {"loop": {"run_id": "loop-t-a"}} if tid == "t-a" and not no_loop else {}
    write(root, "data/results/topic_costs.json", json.dumps(costs))
    write(root, "docs/results/topic_costs.md", "# Cost per topic\n\n" + "\n".join(TOPICS) + "\n")
    loop_stages = ["baseline", "ideate", "subset_exp", "write_up", "audit"]
    report = {"stages": [{"stage": s} for s in loop_stages], "total_cost_usd": 0.2, "audit": {"overall": "green"}}
    write(root, "data/results/run_loop-t-a.json", json.dumps(report))
    ledger_file(root, "loop-t-a", 0.2)


def test_topic_runs_check_passes_three_completed_topics_and_a_loop_run(tmp_path: Path) -> None:
    topic_runs_fixture(tmp_path)
    result = run("check_topic_runs.py", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "loop run loop-t-a audit green" in result.stdout


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"incomplete": "t-b"}, "did not complete"), ({"self_graded": True}, "not independent"),
     ({"no_audit": True}, "no audit result"), ({"no_reading": True}, "reading of the parent selection"),
     ({"no_loop": True}, "no topic has a research-loop run"), ({"drop_stage": "parent"}, "stages not recorded"),
     ({"ledger_drift": True}, "differs from the ledger"), ({"over_cap": True}, "per-topic cap")],
)  # fmt: skip
def test_topic_runs_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    topic_runs_fixture(tmp_path, **kwargs)
    result = run("check_topic_runs.py", tmp_path)
    assert result.returncode == 2
    assert message in result.stderr


# ── judge_retest_3 ────────────────────────────────────────────────────────────


def retest3_fixture(root: Path, *, drift: bool = False, few_real: bool = False, no_miss: bool = False,
                    bad_accounting: bool = False, over_cap: bool = False,
                    wrong_split: bool = False) -> None:  # fmt: skip
    import hashlib  # noqa: PLC0415

    agree = {"k": 80, "n": 85, "rate": 0.94, "ci95": [0.87, 0.97]}
    cb = {"test_sha256": "a" * 64, "n_test": 85}
    write(root, "data/claim_bench/split.json", json.dumps(cb))
    write(root, "data/ledger/run_cb.jsonl", "")
    spend = {"routing_and_dev": 0.01, "reference": 1.5 if over_cap else 0.4}
    results = {"test_sha256": "b" * 64 if wrong_split else "a" * 64, "test_items": 85,
               "dev": {"arms": {"glm_direct": {}, "jev_glm": {}}, "chosen": "jev_glm"},
               "test": {"chosen_path": {"agreement": agree}, "reference": {"agreement": agree}},
               "spend_usd": spend, "ledger": "data/ledger/run_cb.jsonl"}  # fmt: skip
    write(root, "data/claim_bench/results.json", json.dumps(results))
    n_real = 12 if few_real else 30
    rows = "id,topic,source,supported,labelled_by,note\n" + "".join(f"r{i},t,R1,yes,helper,\n" for i in range(n_real))
    write(root, "data/claim_bench/real_claims_labels.csv", rows)
    real_agree = {"k": 27, "n": n_real, "rate": 0.9, "ci95": [0.74, 0.97]}
    real = {"n": n_real, "paths": {"glm_direct": {"agreement": real_agree}, "jev_glm": {"agreement": real_agree}},
            "reference": {"agreement": real_agree}, "labels": "an AI helper",
            "spend_usd": {"reference": 0.2}}  # fmt: skip
    write(root, "data/claim_bench/real_results.json", json.dumps(real))
    items = [json.dumps({"id": f"x{i}", "label": True}) for i in range(10)]
    digest = hashlib.sha256("\n".join(sorted(items)).encode("utf-8")).hexdigest()
    write(root, "data/retest3/items.jsonl", "\n".join(items) + ("\nextra" if drift else "") + "\n")
    write(root, "data/retest3/split.json", json.dumps({"test_sha256": digest}))
    write(root, "data/ledger/run_rt.jsonl", "")
    a10 = {"k": 9, "n": 10, "rate": 0.9, "ci95": [0.6, 0.98]}
    misses = [] if no_miss else [{"id": "retest-0008"}, {"id": "retest-0038"}]
    rr = {"test_sha256": digest, "items": 10, "decided_path": {"agreement": a10}, "reference": {"agreement": a10},
          "t1_reverse_if_1": {"fired": True}, "increment2_confident_misses": misses,
          "idea_worth_run": {"score_counts": {"3": 1}}, "spend_usd": {"reference": 0.1},
          "ledger": "data/ledger/run_rt.jsonl"}  # fmt: skip
    write(root, "data/retest3/results.json", json.dumps(rr))
    acc = {"records": 7 if bad_accounting else 5, "by_question": {"lit.a": {"records": 2, "disposition": "x"},
                                                                  "loop.b": {"records": 3,
                                                                             "disposition": "y"}}}  # fmt: skip
    write(root, "data/retest3/accounting.json", json.dumps(acc))


def test_retest3_check_passes_a_complete_retest(tmp_path: Path) -> None:
    retest3_fixture(tmp_path)
    result = run("check_retest3.py", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "T1 reverse-if 1 fired: True" in result.stdout


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"drift": True}, "items changed"), ({"few_real": True}, "at least 30"), ({"no_miss": True}, "confident misses"),
     ({"bad_accounting": True}, "do not add up"), ({"over_cap": True}, "over the cap"),
     ({"wrong_split": True}, "different test set")],
)  # fmt: skip
def test_retest3_check_blocks(tmp_path: Path, kwargs: dict, message: str) -> None:
    retest3_fixture(tmp_path, **kwargs)
    result = run("check_retest3.py", tmp_path)
    assert result.returncode == 2
    assert message in result.stderr

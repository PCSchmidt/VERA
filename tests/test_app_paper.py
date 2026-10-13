# ruff: noqa: E501
"""The "Make a paper from this review" button's server side, the paper reader and its PDF (APP-F-04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from tests.test_app_core import KEY  # noqa: E402
from tests.test_app_server import BODY, make  # noqa: E402
from vera.app import state as app_state  # noqa: E402

RUN = "my-first-run"
PAPER = {"max_usd": 0.75, "length_words": 3000, "emphasis": None}


def finished_review(tmp_path: Path, light: str = "green") -> Path:
    run_dir = tmp_path / "runs" / RUN
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "audit_report.json").write_text(json.dumps({"overall": light}), encoding="utf-8")
    (run_dir / "retrieved.jsonl").write_text(
        json.dumps({"key": "R1", "title": "Candès on shift", "authors": ["A. Author"], "year": "2024", "url": "u",
                    "id": "arXiv:1"}) + "\n", encoding="utf-8")  # fmt: skip
    app_state.write(run_dir, "complete", None)
    return run_dir


def written_paper(run_dir: Path) -> None:
    out = run_dir / "paper"
    out.mkdir(exist_ok=True)
    md = ("# Agent traces: a review\n\n## Abstract\n\nThis paper reviews.\n\n## Findings\n\nA claim long enough to quote [R1].\n\n"
          "## Discussion\n\n*Interpretation: VERA's reading of the claims named after each statement, judged to follow from "
          "them; not checked against quotes.*\n\nTraces may help (C1).\n\n## References\n\n[R1] A. Author. Candès on shift. 2024.\n")  # fmt: skip
    (out / "paper.md").write_text(md, encoding="utf-8")
    claim = {"id": "C1", "claim": "A claim long enough to quote", "source_key": "R1", "quote": "the exact quote",
             "locator": "abstract", "quote_check": "pass"}  # fmt: skip
    (out / "claims.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
    doc = {"title": "Agent traces: a review", "question": "What do traces hold?",
           "sections": [{"heading": "Abstract", "kind": "summary"}, {"heading": "Findings", "kind": "evidence"},
                        {"heading": "Discussion", "kind": "interpretation"}],
           "inferences": [{"id": "I1", "section": "Discussion", "text": "Traces may help", "premises": ["C1"], "status": "pass"},
                          {"id": "I2", "section": "Discussion", "text": "Traces prove all", "premises": ["C1"],
                           "status": "removed", "reason": "does not follow from its premises"}]}  # fmt: skip
    (out / "paper.json").write_text(json.dumps(doc), encoding="utf-8")
    report = {"overall": "green", "checks_run": ["citation", "claim_support", "inference"], "findings": []}
    (out / "audit_report.json").write_text(json.dumps(report), encoding="utf-8")


def started(tmp_path: Path, monkeypatch, light: str = "green"):
    client, session, launches, _ = make(tmp_path, monkeypatch)
    client.post("/api/key", json={"key": KEY})
    client.post("/api/runs", json=BODY)
    return client, launches, finished_review(tmp_path, light)


def test_APP_F_04_the_paper_starts_only_from_a_finished_review_that_did_not_fail(tmp_path: Path, monkeypatch) -> None:
    client, launches, run_dir = started(tmp_path, monkeypatch, light="red")
    assert client.post(f"/api/runs/{RUN}/review-paper", json=PAPER).status_code == 409  # a red audit
    (run_dir / "artifacts" / "audit_report.json").write_text(json.dumps({"overall": "green"}), encoding="utf-8")
    app_state.write(run_dir, "running", None)
    assert client.post(f"/api/runs/{RUN}/review-paper", json=PAPER).status_code == 409  # not finished
    app_state.write(run_dir, "complete", None)
    for bad in (
        {**PAPER, "max_usd": 0},
        {**PAPER, "max_usd": 30},
        {**PAPER, "length_words": 4000},
        {**PAPER, "key": KEY},
    ):
        assert client.post(f"/api/runs/{RUN}/review-paper", json=bad).status_code == 422
    assert client.get(f"/api/runs/{RUN}/review-paper/status").status_code == 404  # nothing was started
    r = client.post(f"/api/runs/{RUN}/review-paper", json=PAPER)
    assert r.status_code == 200 and r.json()["state"] == "queued" and r.json()["max_usd"] == 0.75
    run_id, phase, env = launches.calls[-1]
    assert (run_id, phase) == (RUN, "paper") and env["OPENROUTER_API_KEY"] == KEY  # the key goes to the worker only
    assert KEY not in (run_dir / "paper" / "app_paper_request.json").read_text("utf-8")
    assert client.post(f"/api/runs/{RUN}/review-paper", json=PAPER).status_code == 409  # one paper per review


def test_APP_F_04_the_paper_has_its_own_cap_stop_and_resume(tmp_path: Path, monkeypatch) -> None:
    client, launches, run_dir = started(tmp_path, monkeypatch)
    ledger = tmp_path / "data" / "ledger" / f"run_{RUN}.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"cost_usd": 0.16}) + "\n", encoding="utf-8")  # what the review spent
    client.post(f"/api/runs/{RUN}/review-paper", json=PAPER)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"cost_usd": 0.05}) + "\n")  # the paper's first call
    app_state.write(run_dir / "paper", "running", None)
    st = client.get(f"/api/runs/{RUN}/review-paper/status").json()
    assert abs(st["spent_usd"] - 0.05) < 1e-9 and st["max_usd"] == 0.75  # the paper's spend, not the run's
    assert client.post(f"/api/runs/{RUN}/review-paper/stop").json()["state"] == "stopping"
    assert (run_dir / "STOP").exists()  # the run's own stop file: the next model call notices it
    assert app_state.read(run_dir)["state"] == "complete"  # the review's own state is untouched
    assert client.post(f"/api/runs/{RUN}/review-paper/resume").status_code == 409  # still stopping
    app_state.write(run_dir / "paper", "stopped", None)
    assert client.post(f"/api/runs/{RUN}/review-paper/resume").json()["state"] == "queued"
    assert launches.calls[-1][1] == "paper_resume"


def test_APP_F_04_the_reader_and_the_pdf_mark_interpretation(tmp_path: Path, monkeypatch) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    client, _, run_dir = started(tmp_path, monkeypatch)
    client.post(f"/api/runs/{RUN}/review-paper", json=PAPER)
    assert client.get(f"/api/runs/{RUN}/review-paper").status_code == 404  # not written yet
    written_paper(run_dir)
    data = client.get(f"/api/runs/{RUN}/review-paper").json()
    assert data["claims"][0]["id"] == "C1" and data["sources"]["R1"]["title"] == "Candès on shift"
    assert [s["kind"] for s in data["sections"]] == ["summary", "evidence", "interpretation"]
    assert [i["status"] for i in data["inferences"]] == ["pass", "removed"]
    r = client.get(f"/api/runs/{RUN}/review-paper/pdf")
    assert r.status_code == 200 and KEY not in r.content.decode("latin-1")
    text = " ".join(" ".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf")).split())
    for expected in ("REVIEW PAPER", "Interpretation: VERA", "Appendix C", "I1", "removed: does not follow",
                     "judged by a model other than its writer", "Candès", "C1."):  # fmt: skip
        assert expected in text, expected
    assert text.count("Agent traces: a review") == 1  # the title is in the title block, not repeated as a heading


def test_APP_F_04_the_front_end_offers_the_paper_and_hides_it_in_the_static_showcase() -> None:
    js = (Path(__file__).resolve().parents[1] / "vera" / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "Make a paper from this review" in js and "#/paper/" in js and "/review-paper" in js
    assert "make-paper\\/|paper-run\\/|paper\\/" in js  # the static showcase sends these routes to "Run it yourself"
    assert "not checked against quotes" in js  # the form says what is and is not checked


def test_APP_F_04_a_paper_stopped_at_its_budget_resumes_with_a_raised_cap(tmp_path: Path, monkeypatch) -> None:
    client, launches, run_dir = started(tmp_path, monkeypatch)
    client.post(f"/api/runs/{RUN}/review-paper", json=PAPER)
    app_state.write(run_dir / "paper", "stopped", "Stopped at your budget")
    assert client.post(f"/api/runs/{RUN}/review-paper/resume", json={"max_usd": 0.5}).status_code == 409  # lower
    assert client.post(f"/api/runs/{RUN}/review-paper/resume", json={"max_usd": 99}).status_code == 422  # over 25
    r = client.post(f"/api/runs/{RUN}/review-paper/resume", json={"max_usd": 1.0})
    assert r.status_code == 200 and r.json()["max_usd"] == 1.0 and launches.calls[-1][1] == "paper_resume"
    record = json.loads((run_dir / "paper" / "app_paper_request.json").read_text("utf-8"))
    assert record["request"]["max_usd"] == 1.0 and record["request"]["length_words"] == 3000

# ruff: noqa: E501
"""The local web server (APP-F-01, APP-C-01, APP-C-02): local only, never returns the key, drives a run through its states."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from tests.test_app_core import KEY, Launches  # noqa: E402
from vera.app import state as app_state  # noqa: E402
from vera.app.keystore import SessionKey  # noqa: E402
from vera.app.runs import RunError, RunManager  # noqa: E402
from vera.app.server import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BODY = {
    "run_id": "my-first-run",
    "topic": "How do tree ensembles behave under correlated features?",
    "max_usd": 1.0,
    "max_wall_seconds": 3600,
}


def make(tmp_path: Path, monkeypatch, *, key_ok: bool = True):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)
    session, launches = SessionKey(), Launches()
    checked: list[str] = []

    def key_check(key: str) -> None:
        checked.append(key)
        if not key_ok:
            raise RunError("OpenRouter did not accept that key.")

    probes = {"docker": lambda: False, "grobid": lambda: False}
    app = create_app(
        ROOT,
        session=session,
        manager=RunManager(tmp_path, session, launches),
        key_check=key_check,
        probes=probes,
        poll_seconds=0.01,
    )
    return TestClient(app, base_url="http://127.0.0.1"), session, launches, checked


def test_APP_C_02_the_key_is_checked_held_in_memory_and_never_returned(tmp_path: Path, monkeypatch) -> None:
    client, session, launches, checked = make(tmp_path, monkeypatch)
    bodies = []
    r = client.post("/api/key", json={"key": KEY})
    bodies.append(r.text)
    assert r.status_code == 200 and r.json() == {"ok": True, "key_source": "session"} and checked == [KEY]
    assert session.get() == KEY
    bodies.append(client.get("/api/config").text)
    assert client.get("/api/config").json()["key_source"] == "session"
    bodies.append(client.post("/api/runs", json=BODY).text)
    bodies += [client.get("/api/runs").text, client.get("/api/runs/my-first-run").text, client.get("/api/facts").text]
    assert all(KEY not in b for b in bodies)
    assert launches.calls[0][2]["OPENROUTER_API_KEY"] == KEY  # only the worker's environment holds it
    assert client.delete("/api/key").json() == {"ok": True} and not session.present


def test_a_bad_key_is_refused_without_being_kept_or_echoed(tmp_path: Path, monkeypatch) -> None:
    client, session, _, _ = make(tmp_path, monkeypatch, key_ok=False)
    r = client.post("/api/key", json={"key": KEY})
    assert r.status_code == 400 and KEY not in r.text and not session.present
    short = client.post("/api/key", json={"key": "nope"})
    assert short.status_code == 400 and "nope" not in short.text


def test_APP_C_01_only_this_computer_may_use_the_app(tmp_path: Path, monkeypatch) -> None:
    client, *_ = make(tmp_path, monkeypatch)
    assert client.get("/api/config", headers={"host": "evil.example"}).status_code == 403  # DNS rebinding
    assert client.get("/api/config", headers={"host": "192.168.1.5:8765"}).status_code == 403
    cross = client.post("/api/key", json={"key": KEY}, headers={"origin": "https://evil.example"})
    assert cross.status_code == 403 and "Cross-origin" in cross.text
    assert client.post("/api/key", json={"key": KEY}, headers={"origin": "http://127.0.0.1"}).status_code == 200
    resp = client.get("/")
    assert resp.status_code == 200 and "script-src 'self'" in resp.headers["content-security-policy"]
    assert resp.headers["cache-control"] == "no-store"


def test_APP_F_01_a_run_goes_from_form_to_confirmation_to_stop_and_resume(tmp_path: Path, monkeypatch) -> None:
    client, _, launches, _ = make(tmp_path, monkeypatch)
    assert client.post("/api/runs", json=BODY).status_code == 400  # no key yet: a plain-words refusal
    client.post("/api/key", json={"key": KEY})
    assert client.post("/api/runs", json={**BODY, "max_usd": 99}).status_code == 422
    assert client.post("/api/runs", json={**BODY, "extra": 1}).status_code == 422
    st = client.post("/api/runs", json=BODY).json()
    assert st["state"] == "queued" and st["max_usd"] == 1.0 and launches.calls[-1][1] == "start"
    run_dir = tmp_path / "runs" / "my-first-run"
    (run_dir / "scope.json").write_text(
        json.dumps(
            {
                "topic_id": "my-first-run",
                "question": "Does X hold?",
                "why_researchable": "w",
                "empirical": False,
                "candidate_parent": None,
                "no_parent_reason": "n",
                "status": "proposed",
            }
        ),
        encoding="utf-8",
    )
    app_state.write(run_dir, "awaiting_confirmation", "Check the question")
    assert client.get("/api/runs/my-first-run/scope").json()["question"] == "Does X hold?"
    with client.stream("GET", "/api/runs/my-first-run/events") as ev:
        text = "".join(ev.iter_text())
    assert text.startswith("data: ") and '"state":"awaiting_confirmation"' in text  # the stream ends at a pause
    done = client.post("/api/runs/my-first-run/confirm", json={"question": "Does X hold under Y?"})
    assert done.status_code == 200 and launches.calls[-1][1] == "continue"
    app_state.write(run_dir, "running", None)
    assert client.post("/api/runs/my-first-run/stop").json()["state"] == "stopping"
    assert client.post("/api/runs/my-first-run/resume").status_code == 409
    app_state.write(run_dir, "stopped", "x")
    assert client.post("/api/runs/my-first-run/resume").json()["state"] == "queued"
    assert client.get("/api/runs/nope-nope").status_code == 404 and client.get("/api/runs/..%2f..").status_code in {
        404,
        422,
    }


def test_the_examples_open_with_their_evidence_and_nothing_outside_their_folder(tmp_path: Path, monkeypatch) -> None:
    client, *_ = make(tmp_path, monkeypatch)
    facts = client.get("/api/facts").json()
    assert len(facts["examples"]) == 4
    paper = client.get("/api/examples/tree-explain/paper").json()
    assert paper["markdown"].startswith("## Abstract") and paper["audit"]["overall"] in {"green", "amber", "red"}
    review = client.get("/api/examples/conformal-shift/paper").json()
    assert review["claims"] and review["claims"][0]["quote"] and review["sources"]
    assert client.get("/api/examples/tree-explain/files/figures/fig_rank_stability.png").status_code == 200
    assert client.get("/api/examples/tree-explain/files/results.json").status_code == 200
    for bad in ("../runs4-credal/paper.md", "..%2f..%2f..%2f.env", "run_report.sh", "../../../pyproject.toml"):
        assert client.get(f"/api/examples/tree-explain/files/{bad}").status_code in {404, 422}
    assert client.get("/api/examples/not-an-example/paper").status_code == 404


def test_the_pdf_of_an_example_carries_its_text_tables_figures_and_evidence(tmp_path: Path, monkeypatch) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    client, *_ = make(tmp_path, monkeypatch)
    r = client.get("/api/examples/tree-explain/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert 'filename="vera-example-tree-explain.pdf"' in r.headers["content-disposition"] and r.content[:5] == b"%PDF-"
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    text = " ".join(p.get_text() for p in doc)
    assert doc.page_count >= 4 and "RESEARCH PAPER" in text and "Appendix A. The audit" in text
    assert "Component error against the true decomposition" in text  # a table's heading and a figure's caption
    assert sum(len(p.get_images()) for p in doc) >= 3  # the three figures are in the file
    review = pymupdf.open(stream=client.get("/api/examples/conformal-shift/pdf").content, filetype="pdf")
    rtext = " ".join(p.get_text() for p in review)
    assert (
        "Candès" in rtext and "Appendix B. Claims and the passages" in rtext and "LITERATURE REVIEW" in rtext
    )  # non-ASCII names, the evidence
    assert client.get("/api/examples/not-an-example/pdf").status_code == 404


def test_the_pdf_of_a_run_is_built_from_the_runs_own_files(tmp_path: Path, monkeypatch) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    client, *_ = make(tmp_path, monkeypatch)
    client.post("/api/key", json={"key": KEY})
    client.post("/api/runs", json=BODY)
    run_dir = tmp_path / "runs" / "my-first-run"
    (run_dir / "artifacts").mkdir()
    (run_dir / "literature.md").write_text(
        "## Literature review\n\nA claim long enough to quote [R1].\n\n## References\n\n[R1] A. Author. A title. 2024.\n[R2] B. Author. Another. 2023.\n",
        encoding="utf-8",
    )
    (run_dir / "claims.jsonl").write_text(
        json.dumps(
            {
                "claim": "A claim long enough to quote",
                "source_key": "R1",
                "quote": "the exact quote",
                "locator": "abstract",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "artifacts" / "audit_report.json").write_text(
        json.dumps(
            {"overall": "amber", "checks_run": ["citation"], "findings": [{"severity": "warn", "summary": "a lead"}]}
        ),
        encoding="utf-8",
    )
    r = client.get("/api/runs/my-first-run/pdf")
    assert r.status_code == 200 and KEY not in r.content.decode("latin-1")
    text = " ".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
    assert "AMBER" in text and "the exact quote" in text and "[R2] B. Author" in text and "a lead" in text
    assert client.get("/api/runs/nope-nope/pdf").status_code == 404


def test_APP_C_03_the_server_answers_only_this_computer_and_loads_nothing_from_outside(
    tmp_path: Path, monkeypatch
) -> None:
    client, *_ = make(tmp_path, monkeypatch)
    assert (
        client.get("/api/config", headers={"host": "evil.example"}).status_code == 403
    )  # another host name (DNS rebinding)
    cross = client.post("/api/key", json={"key": KEY}, headers={"origin": "https://evil.example"})
    assert cross.status_code == 403  # a page elsewhere cannot drive it
    page = client.get("/").text
    assert not re.search(r'(src|href)="https?://', page)  # nothing is loaded from outside the machine
    assert "default-src 'self'" in client.get("/").headers["content-security-policy"]

# ruff: noqa: E501
"""APP-C-01 and APP-C-02, tried adversarially: a key with a distinctive marker goes in, a run fails in the worst way (the
provider echoes the key in its error), and the marker must appear in no file, status, message or process argument."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.lit_fakes import LitJudge, make_lit_spec
from tests.test_app_core import KEY, REQUEST
from vera.app import runs as runs_module
from vera.app import worker
from vera.app.appbudget import AppBudget
from vera.app.keystore import SessionKey
from vera.app.runs import RunManager
from vera.backends import redact
from vera.backends.generator import OpenRouterGenerator
from vera.backends.openrouter import Prices
from vera.ledger import Ledger
from vera.literature.deps import LitDeps


def test_APP_C_02_redact_removes_a_key_this_process_holds(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert KEY not in redact(f"HTTP 401: invalid credentials {KEY} for this request")
    assert redact("nothing secret here") == "nothing secret here"


def all_text(root: Path) -> str:
    chunks = []
    for p in root.rglob("*"):
        if p.is_file():
            chunks.append(p.read_bytes().decode("utf-8", errors="ignore"))
    return "\n".join(chunks)


def echoing_deps(root: Path, request) -> LitDeps:
    """Real OpenRouterGenerator over a transport whose every answer is a 401 that quotes the key back."""

    def handler(req: httpx.Request) -> httpx.Response:
        token = req.headers["authorization"].removeprefix("Bearer ")
        return httpx.Response(401, text=f'{{"error": "invalid credentials: {token}"}}')

    spec = make_lit_spec(request.run_id)
    run_dir = root / "runs" / request.run_id
    budget = AppBudget(**spec.budget.model_dump()).watch(run_dir)
    ledger = Ledger.for_run(request.run_id, root=root / "data" / "ledger", resume=False)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    generator = OpenRouterGenerator("sonnet", "anthropic/claude-sonnet-5.5", ledger=ledger, budget=budget, client=client,
                                    prices=Prices(input_per_token=1e-6, output_per_token=1e-6))  # fmt: skip
    return LitDeps(
        spec=spec, generator=generator, judge=LitJudge(ledger, budget), budget=budget, run_dir=run_dir, ledger=ledger
    )


@pytest.mark.parametrize("phase", ["start"])
def test_APP_C_02_a_provider_that_echoes_the_key_leaves_it_in_no_file_or_status(
    tmp_path: Path, monkeypatch, phase: str
) -> None:
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)  # no .env there
    monkeypatch.setattr(worker, "real_deps", lambda root, request, resume: echoing_deps(root, request))
    monkeypatch.setattr("vera.backends.time.sleep", lambda s: None)
    session = SessionKey()
    session.set(KEY)

    def launch(run_id: str, ph: str, env: dict) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", env["OPENROUTER_API_KEY"])  # what the worker process would have
        worker.main([run_id, ph], root=tmp_path)

    mgr = RunManager(tmp_path, session, launch)
    status = mgr.create(REQUEST)
    after = mgr.status(status.run_id)
    assert after.state == "failed" and "could not continue" in (after.message or "")
    assert KEY not in after.model_dump_json()
    assert KEY not in all_text(tmp_path), "the key reached a file"
    assert (
        tmp_path / "runs" / REQUEST.run_id / "worker_error.log"
    ).exists()  # the failure is on record, without the key


def test_APP_C_02_the_key_is_in_the_workers_environment_and_not_its_arguments(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_popen(argv, **kwargs):
        captured["argv"], captured["env"] = argv, kwargs["env"]

    monkeypatch.setattr("vera.sandbox.host.subprocess.Popen", fake_popen)
    runs_module.subprocess_launcher(tmp_path)("my-first-run", "start", {"OPENROUTER_API_KEY": KEY})
    assert KEY not in " ".join(captured["argv"]) and captured["env"]["OPENROUTER_API_KEY"] == KEY
    assert "my-first-run" in captured["argv"] and "start" in captured["argv"]


def test_APP_C_01_nothing_the_app_ships_names_a_maintainer_key() -> None:
    root = Path(__file__).resolve().parents[1]
    for p in (root / "vera" / "app").rglob("*"):
        if p.is_file() and p.suffix in {".py", ".js", ".html", ".css"}:
            text = p.read_text(encoding="utf-8")
            assert "sk-or-v1-" not in text and "Bearer sk-" not in text, p.name


def test_APP_C_02_the_leak_test_has_teeth_it_fails_when_the_redaction_is_removed(tmp_path: Path, monkeypatch) -> None:
    """The adversarial test above would pass if nothing could leak. With the redaction taken out the same run must put the key on disk."""
    monkeypatch.setattr("vera.backends.generator.redact", lambda text: text)
    monkeypatch.setattr("vera.app.worker.redact", lambda text: text)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)
    monkeypatch.setattr(worker, "real_deps", lambda root, request, resume: echoing_deps(root, request))
    monkeypatch.setattr("vera.backends.time.sleep", lambda s: None)
    session = SessionKey()
    session.set(KEY)

    def launch(run_id: str, ph: str, env: dict) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", env["OPENROUTER_API_KEY"])
        worker.main([run_id, ph], root=tmp_path)

    RunManager(tmp_path, session, launch).create(REQUEST)
    assert KEY in all_text(tmp_path), (
        "with no redaction the echoed key should reach the run's log: the leak test would be vacuous"
    )

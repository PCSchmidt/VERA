# ruff: noqa: E501
"""Starting, watching, confirming, stopping and resuming runs (APP-F-01).

A run is a worker process (`vera.app.worker`) over the existing pipeline. This module launches it with the user's key in
its environment only, and reads a run's status back from the files the run writes: the ledger for spend, `gates.jsonl` for
the latest verdict, `app_state.json` for the state word, the final audit file for the light. It computes nothing a run did
not record.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path

from vera.app import pipeline
from vera.app import state as app_state
from vera.app.appbudget import STOP_FILE
from vera.app.keystore import SessionKey
from vera.backends import api_key
from vera.literature import scoping
from vera.sandbox.host import spawn_worker
from vera.schemas import PaperRequest, RunRequest, RunStatus

Launcher = Callable[[str, str, dict[str, str]], None]
LIVE = {"scoping", "running", "stopping"}
RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,63}")
PAPER_DIR = "paper"
PAPER_REQUEST = "app_paper_request.json"  # in runs/<id>/paper/: the button's form and what the run had spent before it
PAPER_STAGES = [("audit_report.json", "audit"), ("inferences.jsonl", "interpret"), ("verify.json", "verify"),
                ("draft.json", "write"), ("outline.json", "outline"), ("passages.jsonl", "widen")]  # fmt: skip


class RunError(ValueError):
    """A request the app refuses, with a reason a person can read."""


def subprocess_launcher(root: Path) -> Launcher:
    def launch(run_id: str, phase: str, env: dict[str, str]) -> None:
        log = root / "runs" / run_id / "worker.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        spawn_worker(run_id, phase, cwd=root, env=env, log=log)

    return launch


class RunManager:
    def __init__(self, root: Path, session: SessionKey, launcher: Launcher | None = None) -> None:
        self.root, self.session = root, session
        self.launcher = launcher or subprocess_launcher(root)

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID.fullmatch(run_id):
            raise RunError("That is not a valid run id.")
        return self.root / "runs" / run_id

    def _env(self) -> dict[str, str]:
        """The worker's environment: the session key goes in as OPENROUTER_API_KEY, here and nowhere else."""
        env = dict(os.environ)
        key = self.session.get()
        if key:
            env["OPENROUTER_API_KEY"] = key
        elif not env.get("OPENROUTER_API_KEY"):
            try:
                api_key("OPENROUTER_API_KEY")
            except KeyError as exc:
                raise RunError(
                    "Connect your OpenRouter key first: none is set for this session or your environment."
                ) from exc
        return env

    def _launch(self, run_id: str, phase: str) -> None:
        self.launcher(run_id, phase, self._env())

    def create(self, request: RunRequest) -> RunStatus:
        run_dir = self.run_dir(request.run_id)
        if run_dir.exists() or (self.root / "data" / "ledger" / f"run_{request.run_id}.jsonl").exists():
            raise RunError("A run with that name already exists; pick another name.")
        env = self._env()  # refuse before creating anything when there is no key
        run_dir.mkdir(parents=True)
        (run_dir / "app_request.json").write_text(request.model_dump_json(indent=1), encoding="utf-8")
        app_state.write(run_dir, "queued", None)
        self.launcher(request.run_id, "start", env)
        return self.status(request.run_id)

    def confirm(self, run_id: str, question: str | None) -> RunStatus:
        run_dir = self.run_dir(run_id)
        if app_state.read(run_dir).get("state") != "awaiting_confirmation":
            raise RunError("This run is not waiting for a confirmation.")
        pipeline.confirm(run_dir, question)
        app_state.write(run_dir, "queued", None)
        self._launch(run_id, "continue")
        return self.status(run_id)

    def stop(self, run_id: str) -> RunStatus:
        run_dir = self.run_dir(run_id)
        if app_state.read(run_dir).get("state") not in LIVE:
            raise RunError("This run is not running.")
        (run_dir / STOP_FILE).write_text("stop requested\n", encoding="utf-8")
        app_state.write(run_dir, "stopping", "Stopping at the next safe point; nothing already done is lost.")
        return self.status(run_id)

    def resume(self, run_id: str) -> RunStatus:
        run_dir = self.run_dir(run_id)
        if app_state.read(run_dir).get("state") not in {"stopped", "failed"}:
            raise RunError("Only a stopped run can be resumed.")
        app_state.write(run_dir, "queued", None)
        self._launch(run_id, "resume")
        return self.status(run_id)

    # ── the review paper (APP-F-04): its own state, cap and audit, beside the review's ──────────────────

    def paper_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / PAPER_DIR

    def _spent(self, run_id: str) -> float:
        ledger = self.root / "data" / "ledger" / f"run_{run_id}.jsonl"
        if not ledger.exists():
            return 0.0
        return sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip())

    def make_paper(self, run_id: str, request: PaperRequest) -> RunStatus:
        review = self.status(run_id)
        if review.state != "complete" or review.audit not in {"green", "amber"}:
            raise RunError("A paper can be made only from a finished review whose audit did not fail.")
        folder = self.paper_dir(run_id)
        if app_state.read(folder).get("state") is not None:
            raise RunError("This review already has a paper (or one is being made).")
        env = self._env()
        folder.mkdir(parents=True, exist_ok=True)
        record = {"request": request.model_dump(mode="json"), "spent_before_usd": self._spent(run_id)}
        (folder / PAPER_REQUEST).write_text(json.dumps(record, indent=1), encoding="utf-8")
        app_state.write(folder, "queued", None)
        self.launcher(run_id, "paper", env)
        return self.paper_status(run_id)

    def stop_paper(self, run_id: str) -> RunStatus:
        folder = self.paper_dir(run_id)
        if app_state.read(folder).get("state") not in LIVE:
            raise RunError("No paper is being made for this review.")
        (self.run_dir(run_id) / STOP_FILE).write_text("stop requested\n", encoding="utf-8")
        app_state.write(folder, "stopping", "Stopping at the next safe point; nothing already done is lost.")
        return self.paper_status(run_id)

    def resume_paper(self, run_id: str, max_usd: float | None = None) -> RunStatus:
        """Resume a stopped paper; `max_usd`, when given, raises its cap (a paper stopped at its budget needs that)."""
        folder = self.paper_dir(run_id)
        if app_state.read(folder).get("state") not in {"stopped", "failed"}:
            raise RunError("Only a stopped paper can be resumed.")
        if max_usd is not None:
            path = folder / PAPER_REQUEST
            record = json.loads(path.read_text(encoding="utf-8"))
            if max_usd < record["request"]["max_usd"]:
                raise RunError("A resumed paper's cap can be raised, not lowered.")
            record["request"] = PaperRequest.model_validate({**record["request"], "max_usd": max_usd}).model_dump(mode="json")
            path.write_text(json.dumps(record, indent=1), encoding="utf-8")
        app_state.write(folder, "queued", None)
        self._launch(run_id, "paper_resume")
        return self.paper_status(run_id)

    def paper_status(self, run_id: str) -> RunStatus | None:
        folder = self.paper_dir(run_id)
        st = app_state.read(folder)
        if not st:
            return None
        record = json.loads((folder / PAPER_REQUEST).read_text(encoding="utf-8"))
        stage = next((name for f, name in PAPER_STAGES if (folder / f).exists()), None)
        report = folder / "audit_report.json"
        light = json.loads(report.read_text(encoding="utf-8")).get("overall") if report.exists() else None
        return RunStatus(
            run_id=run_id, state=st.get("state", "queued"), stage=stage,
            spent_usd=round(max(self._spent(run_id) - record["spent_before_usd"], 0.0), 6),
            max_usd=record["request"]["max_usd"], started_at=st.get("started_at"), updated_at=st.get("updated_at"),
            last_verdict=self._last_verdict(self.run_dir(run_id)), message=st.get("message"),
            audit=light if light in {"green", "amber", "red"} else None,
        )  # fmt: skip

    def status(self, run_id: str) -> RunStatus:
        run_dir = self.run_dir(run_id)
        request = RunRequest.model_validate_json((run_dir / "app_request.json").read_text(encoding="utf-8"))
        st = app_state.read(run_dir)
        ledger = self.root / "data" / "ledger" / f"run_{run_id}.jsonl"
        spent = 0.0
        if ledger.exists():
            spent = sum(
                json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()
            )
        return RunStatus(
            run_id=run_id, state=st.get("state", "queued"), stage=self._stage(run_dir), spent_usd=round(spent, 6),
            max_usd=request.max_usd, started_at=st.get("started_at"), updated_at=st.get("updated_at"),
            last_verdict=self._last_verdict(run_dir), message=st.get("message"), audit=self._audit(run_dir),
        )  # fmt: skip

    @staticmethod
    def _stage(run_dir: Path) -> str | None:
        best = run_dir / "best_so_far.json"
        if best.exists():
            done = json.loads(best.read_text(encoding="utf-8")).get("stages_completed") or []
            if done:
                return done[-1]
        return "scope" if (run_dir / scoping.SCOPE_FILE).exists() else None

    @staticmethod
    def _last_verdict(run_dir: Path) -> dict | None:
        path = run_dir / "gates.jsonl"
        if not path.exists():
            return None
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return None
        rec = json.loads(lines[-1])
        v = rec.get("verdict") or {}
        return {"question": (rec.get("question") or {}).get("id"), "answer": v.get("answer"),
                "confidence": v.get("confidence"), "backend": v.get("backend")}  # fmt: skip

    @staticmethod
    def _audit(run_dir: Path) -> str | None:
        path = run_dir / "artifacts" / "audit_report.json"
        if path.exists():
            light = json.loads(path.read_text(encoding="utf-8")).get("overall")
            return light if light in {"green", "amber", "red"} else None
        return None

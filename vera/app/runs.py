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
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from vera.app import pipeline
from vera.app import state as app_state
from vera.app.appbudget import STOP_FILE
from vera.app.keystore import SessionKey
from vera.backends import api_key
from vera.literature import scoping
from vera.schemas import RunRequest, RunStatus

Launcher = Callable[[str, str, dict[str, str]], None]
LIVE = {"scoping", "running", "stopping"}
RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,63}")


class RunError(ValueError):
    """A request the app refuses, with a reason a person can read."""


def subprocess_launcher(root: Path) -> Launcher:
    def launch(run_id: str, phase: str, env: dict[str, str]) -> None:
        log = root / "runs" / run_id / "worker.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0  # outlives the server's console
        with log.open("ab") as out:
            subprocess.Popen(  # noqa: S603 - fixed argv, the run id was validated
                [sys.executable, "-m", "vera.app.worker", run_id, phase], cwd=root, env=env, stdout=out, stderr=out,
                creationflags=flags,
            )  # fmt: skip

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

# ruff: noqa: E501
"""The local web server (APP-F-01, APP-F-02, APP-C-02): a thin JSON API over `RunManager`, and the static pages.

It binds to 127.0.0.1 only, refuses any request whose Host or Origin is not this machine (a web page elsewhere cannot drive it,
and DNS rebinding cannot reach it), never returns the key, and accepts the key only in a POST body. Run it with
`uv run vera-app`.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from vera.app import config, facts
from vera.app.keystore import InvalidKey, SessionKey
from vera.app.runs import RunError, RunManager
from vera.literature import scoping
from vera.schemas import AppConfig, RunRequest, RunStatus

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).parent / "static"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
CSP = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
FILE_TYPES = {".png", ".svg", ".json", ".md", ".jsonl"}
TERMINAL = {"awaiting_confirmation", "stopped", "complete", "failed"}
OPENROUTER_KEY_CHECK = "https://openrouter.ai/api/v1/auth/key"


class KeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str


class ConfirmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str | None = None


def check_openrouter_key(key: str) -> None:
    """One inexpensive call that spends nothing: does OpenRouter accept this key? Raises RunError when it does not."""
    try:
        resp = httpx.get(OPENROUTER_KEY_CHECK, headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except httpx.HTTPError as exc:
        raise RunError("Could not reach OpenRouter to check the key. Check your connection and try again.") from exc
    if resp.status_code in {401, 403}:
        raise RunError("OpenRouter did not accept that key.")
    if resp.status_code >= 400:
        raise RunError(f"OpenRouter could not check the key just now (status {resp.status_code}). Try again shortly.")


def create_app(
    root: Path = ROOT,
    *,
    session: SessionKey | None = None,
    manager: RunManager | None = None,
    key_check: Callable[[str], None] = check_openrouter_key,
    probes: dict | None = None,
    poll_seconds: float = 1.0,
) -> FastAPI:
    session = session or SessionKey()
    manager = manager or RunManager(root, session)
    probes = probes or {}
    app = FastAPI(title="VERA", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = urlparse("//" + (request.headers.get("host") or "")).hostname or ""
        if host not in LOCAL_HOSTS:
            return JSONResponse({"detail": "This app answers only on this computer."}, status_code=403)
        origin = request.headers.get("origin")
        if origin and request.method not in {"GET", "HEAD"}:
            o = urlparse(origin)
            same_port = (o.port or 80) == (urlparse("//" + request.headers.get("host", "")).port or 80)
            if (o.hostname or "") not in LOCAL_HOSTS or not same_port:
                return JSONResponse({"detail": "Cross-origin requests are refused."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = CSP
        return response

    def refuse(exc: Exception, code: int = 400):
        raise HTTPException(status_code=code, detail=str(exc))

    @app.get("/api/config", response_model=AppConfig)
    def get_config() -> AppConfig:
        return config.detect(session, **probes)

    @app.post("/api/key")
    def set_key(body: KeyBody) -> dict:
        try:
            probe = SessionKey()
            probe.set(body.key)  # shape first, so a mistyped box never leaves the machine
            key_check(probe.get())
            session.set(body.key)
        except (InvalidKey, RunError) as exc:
            refuse(exc)
        return {"ok": True, "key_source": "session"}  # never the key

    @app.delete("/api/key")
    def forget_key() -> dict:
        session.clear()
        return {"ok": True}

    @app.get("/api/facts")
    def get_facts() -> dict:
        return facts.build_facts(root)

    @app.post("/api/runs", response_model=RunStatus)
    def start_run(body: dict) -> RunStatus:
        try:
            return manager.create(RunRequest.model_validate(body))
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_plain(exc)) from exc
        except RunError as exc:
            refuse(exc)

    @app.get("/api/runs", response_model=list[RunStatus])
    def list_runs() -> list[RunStatus]:
        base = manager.root / "runs"
        out = []
        for d in (
            sorted(base.glob("*/app_request.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if base.exists()
            else []
        ):
            out.append(manager.status(d.parent.name))
        return out

    def run_or_404(run_id: str) -> RunStatus:
        try:
            return manager.status(run_id)
        except (RunError, FileNotFoundError) as exc:
            raise HTTPException(status_code=404, detail="No such run.") from exc

    @app.get("/api/runs/{run_id}", response_model=RunStatus)
    def get_run(run_id: str) -> RunStatus:
        return run_or_404(run_id)

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str) -> StreamingResponse:
        run_or_404(run_id)

        async def stream():
            last = None
            while True:
                status = manager.status(run_id)
                payload = status.model_dump_json()
                if payload != last:
                    yield f"data: {payload}\n\n"
                    last = payload
                if status.state in TERMINAL:
                    return
                await asyncio.sleep(poll_seconds)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/runs/{run_id}/scope")
    def get_scope(run_id: str) -> dict:
        run_or_404(run_id)
        scoped = scoping.read_scope(manager.run_dir(run_id))
        if scoped is None:
            raise HTTPException(status_code=404, detail="No question has been proposed yet.")
        return scoped.model_dump(mode="json")

    @app.post("/api/runs/{run_id}/confirm", response_model=RunStatus)
    def confirm(run_id: str, body: ConfirmBody) -> RunStatus:
        run_or_404(run_id)
        try:
            return manager.confirm(run_id, body.question)
        except RunError as exc:
            refuse(exc, 409)

    @app.post("/api/runs/{run_id}/stop", response_model=RunStatus)
    def stop(run_id: str) -> RunStatus:
        run_or_404(run_id)
        try:
            return manager.stop(run_id)
        except RunError as exc:
            refuse(exc, 409)

    @app.post("/api/runs/{run_id}/resume", response_model=RunStatus)
    def resume(run_id: str) -> RunStatus:
        run_or_404(run_id)
        try:
            return manager.resume(run_id)
        except RunError as exc:
            refuse(exc, 409)

    @app.get("/api/runs/{run_id}/paper")
    def paper(run_id: str) -> dict:
        run_or_404(run_id)
        return read_paper(manager.run_dir(run_id))

    @app.get("/api/examples/{example_id}/paper")
    def example_paper(example_id: str) -> dict:
        match = next((e for e in facts.examples(root) if e["id"] == example_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="No such example.")
        folder = (root / match["document"]).parent
        out = read_paper(folder, document=Path(match["document"]).name, retrieved=match.get("retrieved"), root=root)
        out["example"] = match
        return out

    def safe_file(folder: Path, rel: str) -> FileResponse:
        target = (folder / rel).resolve()
        if folder.resolve() not in target.parents or target.suffix not in FILE_TYPES or not target.is_file():
            raise HTTPException(status_code=404, detail="No such file.")
        return FileResponse(target)

    @app.get("/api/examples/{example_id}/files/{rel:path}")
    def example_file(example_id: str, rel: str) -> FileResponse:
        match = next((e for e in facts.examples(root) if e["id"] == example_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="No such example.")
        return safe_file((root / match["document"]).parent, rel)

    @app.get("/api/runs/{run_id}/files/{rel:path}")
    def run_file(run_id: str, rel: str) -> FileResponse:
        run_or_404(run_id)
        return safe_file(manager.run_dir(run_id), rel)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def _plain(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())


def read_paper(
    folder: Path, document: str | None = None, retrieved: str | None = None, root: Path | None = None
) -> dict:
    """The document, its claims with their quotes, its sources and its audit, as the reader shows them."""
    doc = folder / (document or ("literature.md" if (folder / "literature.md").exists() else "paper.md"))
    text = doc.read_text(encoding="utf-8") if doc.exists() else ""
    claims = _jsonl(folder / "claims.jsonl")
    sources = {
        r["key"]: {k: r.get(k) for k in ("title", "authors", "year", "url", "id")}
        for r in _jsonl(root / retrieved if retrieved and root else folder / "retrieved.jsonl")
    }
    report = folder / "artifacts" / "audit_report.json"
    if not report.exists():
        report = folder / "audit_report.json"
    audit = json.loads(report.read_text(encoding="utf-8")) if report.exists() else None
    audit_md = (folder / "audit.md").read_text(encoding="utf-8") if (folder / "audit.md").exists() else None
    cited = set(re.findall(r"\[(R\d+)\]", text))
    return {"markdown": text, "claims": claims, "sources": {k: v for k, v in sources.items() if k in cited or not cited},
            "audit": audit, "audit_markdown": audit_md}  # fmt: skip


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    import argparse  # noqa: PLC0415

    import uvicorn  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="VERA, the local app: research from a topic, with your own model key.")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    print(f"VERA is running at http://127.0.0.1:{args.port}  (only on this computer; Ctrl+C to stop)")
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

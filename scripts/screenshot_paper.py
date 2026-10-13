"""Screenshots of the review-paper pages (APP-F-04) in light, dark and narrow layouts, from the UI tests' fixture runs.

Serves a fixture root (a finished review with a finished paper, `tests/test_app_ui.py`) on a free local port and has
headless Chrome or Edge save `docs/screenshots/paper-*.png`. The pages show fixture text, not a real run; they record
the layout. Usage: uv run python scripts/screenshot_paper.py
"""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_app_paper import written_paper  # noqa: E402
from tests.test_app_ui import BROWSER, fixture_run  # noqa: E402
from vera.app import state as app_state  # noqa: E402
from vera.app.keystore import SessionKey  # noqa: E402
from vera.app.runs import RunManager  # noqa: E402
from vera.app.server import create_app  # noqa: E402

SHOTS = [  # (file, route, width, height, dark)
    ("paper-light", "paper/paper-run", 1280, 1100, False),
    ("paper-dark", "paper/paper-run", 1280, 1100, True),
    ("paper-narrow", "paper/paper-run", 548, 1600, False),  # headless Chrome will not go narrower than ~500px
    ("makepaper-light", "make-paper/done-run", 1280, 1000, False),
]


def main() -> None:
    if BROWSER is None:
        sys.exit("no headless Chrome or Edge found")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture_run(root, "done-run", "complete", None, "green")
        fixture_run(root, "paper-run", "complete", None, "green")
        written_paper(root / "runs" / "paper-run")
        (root / "runs" / "paper-run" / "paper" / "app_paper_request.json").write_text(
            '{"request": {"max_usd": 0.75, "length_words": 3000, "emphasis": null}, "spent_before_usd": 0.0}',
            encoding="utf-8",
        )
        app_state.write(root / "runs" / "paper-run" / "paper", "complete", None)
        session = SessionKey()
        app = create_app(ROOT, session=session, manager=RunManager(root, session, lambda *a: None),
                         probes={"docker": lambda: False, "grobid": lambda: False})  # fmt: skip
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        threading.Thread(target=srv.run, daemon=True).start()
        while not srv.started:
            time.sleep(0.1)
        out = ROOT / "docs" / "screenshots"
        for name, route, w, h, dark in SHOTS:
            profile = root / f"profile-{name}"  # a fresh profile per load: a shared one can lock
            args = [BROWSER, "--headless=old", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                    "--hide-scrollbars", f"--window-size={w},{h}", "--virtual-time-budget=8000",
                    f"--screenshot={out / (name + '.png')}"]  # fmt: skip
            if dark:
                args.append("--blink-settings=preferredColorScheme=0")
            subprocess.run([*args, f"http://127.0.0.1:{port}/#/{route}"], capture_output=True, timeout=120, check=False)
            print(name, (out / f"{name}.png").stat().st_size if (out / f"{name}.png").exists() else "missing")
        srv.should_exit = True


if __name__ == "__main__":
    main()

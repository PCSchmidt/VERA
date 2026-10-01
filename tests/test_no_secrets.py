"""APP-C-01: no API key in any tracked file (VERA is bring-your-own-key; R11).

Meridian's content rules (.meridian/security-rules.yaml) are enforced on agent
tool calls, not at the commit boundary, so this test is what catches a key
committed from an editor: it runs with the suite at every gate.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# built from parts so this file never matches itself
KEY_PATTERNS = {
    "OpenRouter": re.compile("sk-" + r"or-v1-[0-9a-f]{32,}"),
    "Anthropic": re.compile("sk-" + r"ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI": re.compile("sk-" + r"(proj-)?[A-Za-z0-9]{40,}"),
}


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


def test_APP_C_01_no_api_key_in_tracked_files() -> None:
    found = []
    for path in tracked_files():
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        rel = path.relative_to(ROOT).as_posix()
        found += [f"{rel}: {name} key" for name, rx in KEY_PATTERNS.items() if rx.search(text)]
    assert not found, "API key in tracked files: " + "; ".join(found)


def test_APP_C_01_env_file_is_ignored() -> None:
    assert subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False).returncode == 0

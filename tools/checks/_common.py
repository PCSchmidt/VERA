"""Shared helpers for VERA gate checks.

Checks are stdlib-only so they run before (and independently of) the uv
project. Exit codes follow Meridian: 0 = pass, 2 = block.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NoReturn

BLOCK = 2

# Docs contain em dashes; Windows consoles default to a legacy code page.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def repo_root_arg(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repo root (default: this checkout)",
    )
    return parser


def block(message: str) -> NoReturn:
    print(f"BLOCK: {message}", file=sys.stderr)
    sys.exit(BLOCK)


def ok(message: str) -> None:
    print(f"OK: {message}")


def current_increment(root: Path) -> int:
    """The increment SPEC.md is written for, from its title line."""
    spec = root / "SPEC.md"
    if not spec.exists():
        block("SPEC.md not found; cannot tell the current increment")
    match = re.search(r"Increment\s+(\d+)", spec.read_text(encoding="utf-8"))
    if not match:
        block("SPEC.md title does not name the current increment (e.g. 'Increment 0')")
    return int(match.group(1))

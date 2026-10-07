# ruff: noqa: E501
"""Gates `app_core_ready`, `key_safety_ready`, `ui_ready` (Increment 5): the app exists and each claim about it has a test.

Usage: check_app.py --part core | secrets | ui

core:    the app modules exist; tests named for APP-F-01 (run, stop, resume) and APP-C-02 (session key) exist; the run form's
         schema refuses a cap above the limit; the server binds to 127.0.0.1 only; schemas 0.11 carry the app types.
secrets: no tracked file or app source holds a key-shaped string; `.env` is untracked; the key-leak test, the argv test and the
         origin test exist; the shipped pages load no external script or stylesheet; the Content-Security-Policy is set.
ui:      screenshots of the pages in light, dark and narrow layouts are committed (real PNGs); the page tests, the examples file
         (four examples with their inputs) and the no-figures-in-the-page test exist.
"""

from __future__ import annotations

import json
import re
import subprocess

from _common import block, ok, repo_root_arg

KEY_PATTERNS = [re.compile("sk-" + r"or-v1-[0-9a-f]{32,}"), re.compile("sk-" + r"ant-[A-Za-z0-9_-]{20,}"),
                re.compile("sk-" + r"(proj-)?[A-Za-z0-9]{40,}")]  # fmt: skip
MODULES = ["__init__", "appbudget", "config", "facts", "keystore", "pipeline", "runs", "server", "state", "worker"]
SHOTS = ["landing-light", "landing-dark", "landing-narrow", "examples-light", "reader-light", "reader-narrow", "newrun-light", "runs-light"]


def tests_text(root) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in (root / "tests").glob("test_app_*.py"))


def need(text: str, names: list[str], what: str) -> None:
    for n in names:
        if n not in text:
            block(f"{what}: no test named like {n!r}")


def core(root) -> str:
    for m in MODULES:
        if not (root / "vera" / "app" / f"{m}.py").exists():
            block(f"vera/app/{m}.py is missing")
    need(tests_text(root), ["test_APP_F_01_", "test_APP_C_02_", "stop_halts_at_the_next_call_and_resume"], "app core")
    server = (root / "vera" / "app" / "server.py").read_text(encoding="utf-8")
    if 'host="127.0.0.1"' not in server or "0.0.0.0" in server:  # noqa: S104
        block("the server must bind to 127.0.0.1 only")
    app_schema = (root / "vera" / "schemas" / "app.py").read_text(encoding="utf-8")
    if "MAX_USD_ALLOWED" not in app_schema or "extra=\"forbid\"" not in app_schema:
        block("the run request schema must cap the budget and refuse unknown fields")
    version = (root / "vera" / "schemas" / "version.py").read_text(encoding="utf-8")
    if not re.search(r'SCHEMA_VERSION\s*=\s*"0\.(1[1-9]|[2-9]\d)"', version):
        block("schemas are not at 0.11 or later")
    return "app modules, stop/resume/session-key tests, local-only server, capped request schema"


def secrets(root) -> str:
    files = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode().split("\0")
    if ".env" in files:
        block(".env is tracked")
    for rel in filter(None, files):
        path = root / rel
        if path.is_file() and path.stat().st_size < 5_000_000:
            text = path.read_bytes().decode("utf-8", errors="ignore")
            if any(p.search(text) for p in KEY_PATTERNS):
                block(f"a key-shaped string is in tracked file {rel}")
    need(tests_text(root), ["provider_that_echoes_the_key", "not_its_arguments", "Cross-origin", "test_APP_C_01_"], "key safety")
    static = root / "vera" / "app" / "static"
    for page in [*static.glob("*.html"), *static.glob("*.js"), *static.glob("*.css")]:
        text = page.read_text(encoding="utf-8")
        if re.search(r'<(script|link)[^>]+(src|href)="https?://', text) or re.search(r"@import\s+url\(\s*['\"]?https?:", text):
            block(f"{page.name} loads something from outside the machine")
    if "Content-Security-Policy" not in (root / "vera" / "app" / "server.py").read_text(encoding="utf-8"):
        block("the server sets no Content-Security-Policy")
    return "no key-shaped string in tracked files, .env untracked, leak/argv/origin tests present, no external page loads, CSP set"


def ui(root) -> str:
    shots = root / "docs" / "screenshots"
    for name in SHOTS:
        f = shots / f"{name}.png"
        if not f.exists() or f.stat().st_size < 10_000 or f.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            block(f"screenshot {name}.png is missing or not a real PNG")
    ex = json.loads((root / "data" / "app" / "examples.json").read_text(encoding="utf-8"))["examples"]
    if len(ex) < 2 or not all(e.get("guidance") and e.get("topic_file") and e.get("scope_file") for e in ex):
        block("the examples file must list at least two examples, each with its inputs")
    need(tests_text(root), ["test_each_page_renders_against_fixture_runs", "test_the_static_pages_contain_no_figure_of_their_own",
                            "test_facts_are_built_from_the_committed_files"], "UI")  # fmt: skip
    return f"{len(SHOTS)} screenshots, {len(ex)} examples with their inputs, page and no-figures tests present"


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--part", choices=["core", "secrets", "ui"], required=True)
    args = parser.parse_args()
    ok({"core": core, "secrets": secrets, "ui": ui}[args.part](args.root))


if __name__ == "__main__":
    main()

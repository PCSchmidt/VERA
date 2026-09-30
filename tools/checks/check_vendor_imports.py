"""FND-C-01: no vendor model SDK is imported outside the vera/backends/ package.

Scans every .py file under vera/ and scripts/ (tests and vera/backends/ are
exempt) for `import X` / `from X import ...` where X is a known vendor model
SDK. Keeps vendor lock-in in one place, behind `JudgeBackend`.
"""

from __future__ import annotations

import ast

from _common import block, ok, repo_root_arg

VENDOR_SDKS = {
    "openai", "anthropic", "google.generativeai", "google.genai", "mistralai", "cohere",
    "ollama", "openrouter", "together", "groq", "litellm", "typesafe", "jev",
}  # fmt: skip
SCANNED = ("vera", "scripts")
EXEMPT = ("vera/backends/",)


def vendor_imports(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            if any(name == sdk or name.startswith(sdk + ".") for sdk in VENDOR_SDKS):
                found.append(name)
    return found


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    problems = []
    for top in SCANNED:
        for path in sorted((args.root / top).rglob("*.py")):
            rel = path.relative_to(args.root).as_posix()
            if rel.startswith(EXEMPT):
                continue
            for name in vendor_imports(path.read_text(encoding="utf-8")):
                problems.append(f"{rel} imports {name}")
    if problems:
        block("vendor SDK imported outside vera/backends/ (FND-C-01): " + "; ".join(problems[:8]))
    ok("no vendor SDK imports outside vera/backends/ (FND-C-01)")


if __name__ == "__main__":
    main()

"""FND-F-03: agent-generated code is executed only inside `vera/sandbox/`.

Scans every .py file under vera/ (the sandbox package itself is exempt) for ways to run code in the host process:
`exec`, `eval`, `compile`, `__import__`, `os.system`, `os.popen`, `os.exec*`, `os.spawn*`, `import subprocess`,
`import runpy`, `importlib` loading, and `multiprocessing`. Tests, scripts/ and tools/ are not scanned: they are
VERA's own code, not code the loop wrote. The scan is syntactic; it can't prove a string is never run, but it keeps
every execution path in one reviewed module.
"""

from __future__ import annotations

import ast

from _common import block, ok, repo_root_arg

SCANNED = ("vera",)
EXEMPT = ("vera/sandbox/",)
BANNED_CALLS = {"exec", "eval", "compile", "__import__"}
BANNED_OS = ("system", "popen", "exec", "spawn", "startfile")
BANNED_MODULES = {"subprocess", "runpy", "multiprocessing", "pty", "code", "codeop"}


def violations(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in BANNED_CALLS:
                found.append(f"{fn.id}() at line {node.lineno}")
            elif isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                if fn.value.id == "os" and fn.attr.startswith(BANNED_OS):
                    found.append(f"os.{fn.attr}() at line {node.lineno}")
                if fn.value.id == "importlib" and fn.attr in {"import_module", "reload"}:
                    found.append(f"importlib.{fn.attr}() at line {node.lineno}")
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            if name.split(".")[0] in BANNED_MODULES:
                found.append(f"import {name} at line {node.lineno}")
    return found


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    problems = []
    for top in SCANNED:
        for path in sorted((args.root / top).rglob("*.py")):
            rel = path.relative_to(args.root).as_posix()
            if rel.startswith(EXEMPT):
                continue
            problems += [f"{rel}: {v}" for v in violations(path.read_text(encoding="utf-8"))]
    if problems:
        block("code executed outside vera/sandbox/ (FND-F-03): " + "; ".join(problems[:8]))
    ok("no exec/eval/subprocess outside vera/sandbox/ (FND-F-03)")


if __name__ == "__main__":
    main()

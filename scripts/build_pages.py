# ruff: noqa: E501
"""Build the read-only GitHub Pages showcase into a folder (default `_site`).

The showcase is the app's own front end (`vera/app/static/`) in static mode: no server, no key, nothing that runs a model. Everything it shows
is generated from files already committed to the repository: `data/app/showcase.json` lists the examples; each example's review or paper,
claims, quotes, audit and figures come from its folder; the landing page's figures come from the example ledgers and the rubric file
(`vera.app.facts`); and each example is also rendered to a PDF with the same writer the app uses. Paths are relative, so the site works under
`https://<user>.github.io/<repo>/`.

Usage: uv run python scripts/build_pages.py [--out _site]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from vera.app import facts
from vera.app.pdf import render_pdf
from vera.app.server import read_paper

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "vera" / "app" / "static"
SHOWCASE = "showcase.json"
KEY_SHAPES = [re.compile("sk-" + r"or-v1-[0-9a-f]{32,}"), re.compile("sk-" + r"ant-[A-Za-z0-9_-]{20,}"), re.compile("sk-" + r"(proj-)?[A-Za-z0-9]{40,}")]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def build(out: Path, root: Path = ROOT) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # the front end, with relative asset paths and the static-mode switch
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/static/app.css"', 'href="app.css"').replace('<script src="/static/app.js"></script>', '<script src="static-config.js"></script>\n<script src="app.js"></script>')
    (out / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(STATIC / "app.css", out / "app.css")
    shutil.copy(STATIC / "app.js", out / "app.js")
    (out / "static-config.js").write_text("window.VERA_STATIC = true;\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    all_facts = facts.build_facts(root, SHOWCASE)
    write_json(out / "data" / "facts.json", all_facts)
    for ex in all_facts["examples"]:
        folder = (root / ex["document"]).parent
        paper = read_paper(folder, document=Path(ex["document"]).name, retrieved=ex.get("retrieved"), root=root)
        paper["example"] = ex
        write_json(out / "data" / "examples" / ex["id"] / "paper.json", paper)
        for rel in ("results.json",):
            if (folder / rel).exists():
                dest = out / "data" / "examples" / ex["id"] / "files" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(folder / rel, dest)
        if (folder / "figures").is_dir():
            shutil.copytree(folder / "figures", out / "data" / "examples" / ex["id"] / "files" / "figures")
        meta = {"title": ex["title"], "question": ex["question"], "kind": ex["kind"], "run_id": ex["id"], "date": "", "spent_usd": ex["spent_usd"], "cap_usd": ex["budget_cap_usd"]}
        (out / "pdf").mkdir(exist_ok=True)
        (out / "pdf" / f"{ex['id']}.pdf").write_bytes(render_pdf(paper, meta, folder))

    # nothing key-shaped may be published
    for path in out.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".js", ".html", ".css"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(p.search(text) for p in KEY_SHAPES):
                raise SystemExit(f"a key-shaped string is in {path.relative_to(out)}: not publishing")
    return all_facts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "_site")
    args = ap.parse_args()
    built = build(args.out)
    n = sum(1 for _ in args.out.rglob("*") if _.is_file())
    print(f"built {len(built['examples'])} examples, {n} files, into {args.out}")


if __name__ == "__main__":
    main()

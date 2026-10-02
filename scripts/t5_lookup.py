"""Trade T5 measurement: how well do free bibliographic sources find real references? (docs/04 T5)

Sample: the 10 T3 papers (data/t3_sample.json). For each, up to N references drawn by seed from
  - the generated paper's GROBID reference list (data/cache/bench/refs/), which may hold fabricated entries, and
  - its parent paper's reference list (GROBID on data/raw/parents/), which holds real papers, so a miss there is a
    coverage gap or a parse error, not a fabrication.
Every sampled reference is looked up by title in Crossref, OpenAlex, arXiv and Semantic Scholar. A hit is a top-3
candidate whose normalised title is >= 0.90 similar and whose year is within 1 (or missing on either side).

Politeness: a User-Agent naming the project, no email, one request at a time per source with a pause, 429/5xx
retried with back-off. Results are cached per source in data/cache/t5/<source>.jsonl, so a run can stop and resume
(`--max-seconds`; the agent's background limit is 10 minutes). Output summary: `--report`.

Usage: uv run python scripts/t5_lookup.py --source crossref|openalex|arxiv|s2 [--max-seconds 540]
       uv run python scripts/t5_lookup.py --prepare   # draw the sample (GROBID on the parents; needs GROBID up)
       uv run python scripts/t5_lookup.py --report
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "t5"
SAMPLE = CACHE / "sample.json"
SEED = 20261003
PER_SET = 15
MIN_TITLE = 15
UA = "VERA-research/0.1 (+https://github.com/PCSchmidt/VERA; reference-existence checks)"
PAUSE = {"crossref": 0.3, "openalex": 0.2, "arxiv": 3.1, "s2": 1.1}


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def slug(paper_id: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in paper_id)


def key(title: str) -> str:
    return hashlib.sha1(norm(title).encode()).hexdigest()[:16]


# ── sample ──────────────────────────────────────────────────────────────────────────────────────────


def prepare() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from grobid_refs import references  # noqa: PLC0415 - needs a running GROBID

    inv = {
        r["gen_paper_id"]: r for r in csv.DictReader((ROOT / "data" / "corpus_inventory.csv").open(encoding="utf-8"))
    }
    papers = json.loads((ROOT / "data" / "t3_sample.json").read_text(encoding="utf-8"))["papers"]
    rng = random.Random(SEED)
    out = []
    for p in papers:
        row = (
            inv[p]
            if p in inv
            else next(r for k, r in inv.items() if slug(k) == slug(p) or k.replace(" ", "_") == p.replace(" ", "_"))
        )
        gen_refs = json.loads(
            (ROOT / "data" / "cache" / "bench" / "refs" / f"{slug(row['gen_paper_id'])}.json").read_text(
                encoding="utf-8"
            )
        )["refs"]
        pid = row["parent_id_arxiv_or_doi"]
        pdf = ROOT / "data" / "raw" / "parents" / (f"{pid.replace(':', '_')}.pdf")
        parent_refs = references(pdf)
        for kind, refs in (("generated", gen_refs), ("parent", parent_refs)):
            usable = [r for r in refs if len(r["title"]) >= MIN_TITLE]
            drawn = rng.sample(usable, min(PER_SET, len(usable)))
            out.append({"paper": row["gen_paper_id"], "kind": kind, "refs_total": len(refs), "refs_usable": len(usable),
                        "refs": [{k: r[k] for k in ("n", "title", "authors", "year")} for r in drawn]})  # fmt: skip
            print(f"{kind:9} {row['gen_paper_id']:45} total={len(refs):3} usable={len(usable):3} drawn={len(drawn)}")
    CACHE.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text(
        json.dumps({"seed": SEED, "per_set": PER_SET, "sets": out}, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def sampled_refs() -> list[dict]:
    seen, refs = set(), []
    for s in json.loads(SAMPLE.read_text(encoding="utf-8"))["sets"]:
        for r in s["refs"]:
            if key(r["title"]) not in seen:
                seen.add(key(r["title"]))
                refs.append(r)
    return refs


# ── sources: each returns candidates [{"title", "year", "id"}] ───────────────────────────────────────


def get(client: httpx.Client, url: str, params: dict, tries: int = 4) -> httpx.Response | None:
    for i in range(tries):
        try:
            resp = client.get(url, params=params)
        except httpx.HTTPError:
            time.sleep(3 * (i + 1))
            continue
        if resp.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (i + 1) * (3 if resp.status_code == 429 else 1))
            continue
        return resp
    return None


def q_crossref(client: httpx.Client, title: str) -> list[dict]:
    r = get(
        client,
        "https://api.crossref.org/works",
        {"query.bibliographic": title, "rows": 3, "select": "title,issued,DOI"},
    )
    if r is None or r.is_error:
        raise RuntimeError(f"crossref {r.status_code if r else 'no response'}")
    out = []
    for it in r.json()["message"]["items"]:
        parts = (it.get("issued") or {}).get("date-parts") or [[None]]
        out.append({"title": (it.get("title") or [""])[0], "year": str(parts[0][0] or ""), "id": it.get("DOI", "")})
    return out


def openalex_key() -> dict:
    """OpenAlex now requires a key (keyless use shares a small daily budget). Read from .env; never logged or cached."""
    from vera.backends import api_key  # noqa: PLC0415

    try:
        return {"api_key": api_key("OPENALEX_API_KEY")}
    except KeyError:
        return {}


def q_openalex(client: httpx.Client, title: str) -> list[dict]:
    r = get(
        client,
        "https://api.openalex.org/works",
        {"search": title, "per-page": 3, "select": "title,publication_year,doi"} | openalex_key(),
    )
    if r is None or r.is_error:
        raise RuntimeError(f"openalex {r.status_code if r else 'no response'}")
    return [{"title": w.get("title") or "", "year": str(w.get("publication_year") or ""), "id": w.get("doi") or ""}
            for w in r.json()["results"]]  # fmt: skip


def q_arxiv(client: httpx.Client, title: str) -> list[dict]:
    words = " ".join(norm(title).split()[:14])
    r = get(client, "https://export.arxiv.org/api/query", {"search_query": f'ti:"{words}"', "max_results": 3})
    if r is None or r.is_error:
        raise RuntimeError(f"arxiv {r.status_code if r else 'no response'}")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(r.text).findall("a:entry", ns):
        out.append({"title": " ".join((e.findtext("a:title", "", ns) or "").split()),
                    "year": (e.findtext("a:published", "", ns) or "")[:4],
                    "id": e.findtext("a:id", "", ns) or ""})  # fmt: skip
    return out


def q_s2(client: httpx.Client, title: str) -> list[dict]:
    r = get(client, "https://api.semanticscholar.org/graph/v1/paper/search/match",
            {"query": title, "fields": "title,year,externalIds"})  # fmt: skip
    if r is None:
        raise RuntimeError("s2 no response")
    if r.status_code == 404:  # "no match"
        return []
    if r.is_error:
        raise RuntimeError(f"s2 {r.status_code}")
    return [{"title": d.get("title") or "", "year": str(d.get("year") or ""), 
             "id": (d.get("externalIds") or {}).get("DOI", "")}
            for d in r.json().get("data", [])]  # fmt: skip


SOURCES = {"crossref": q_crossref, "openalex": q_openalex, "arxiv": q_arxiv, "s2": q_s2}


def cached(source: str) -> dict[str, dict]:
    f = CACHE / f"{source}.jsonl"
    return (
        {json.loads(ln)["key"]: json.loads(ln) for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()}
        if f.exists()
        else {}
    )


def run_source(source: str, max_seconds: float) -> None:
    done, start = cached(source), time.time()
    todo = [r for r in sampled_refs() if key(r["title"]) not in done]
    print(f"{source}: {len(done)} cached, {len(todo)} to look up")
    with (
        httpx.Client(timeout=30, headers={"User-Agent": UA}) as client,
        (CACHE / f"{source}.jsonl").open("a", encoding="utf-8") as out,
    ):
        for r in todo:
            if time.time() - start > max_seconds:
                print("time limit; resume to continue")
                return
            t0 = time.perf_counter()
            try:
                cands, err = SOURCES[source](client, r["title"]), None
            except RuntimeError as exc:
                cands, err = [], str(exc)
            rec = {"key": key(r["title"]), "title": r["title"], "year": r["year"], "cands": cands, "error": err,
                   "latency_s": round(time.perf_counter() - t0, 2)}  # fmt: skip
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(PAUSE[source])
    print(f"{source}: finished")


# ── report ──────────────────────────────────────────────────────────────────────────────────────────


def hit(rec: dict, strict_year: bool = True) -> bool:
    for c in rec["cands"]:
        if sim(rec["title"], c["title"]) >= 0.90:
            if not strict_year or not (rec["year"] and c["year"]) or abs(int(rec["year"]) - int(c["year"])) <= 1:
                return True
    return False


def report() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))["sets"]
    data = {s: cached(s) for s in SOURCES}
    lines = [
        "| Source | Set | Refs | Hit | Hit rate | Title only | Errors | p50 s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    union: dict[str, dict[str, bool]] = {"generated": {}, "parent": {}}
    loose: dict[str, dict[str, bool]] = {"generated": {}, "parent": {}}
    for kind in ("generated", "parent"):
        keys = {key(r["title"]) for s in sample if s["kind"] == kind for r in s["refs"]}
        for src, recs in data.items():
            rs = [recs[k] for k in keys if k in recs]
            hits = sum(hit(r) for r in rs)
            title_only = sum(hit(r, strict_year=False) for r in rs)
            errs = sum(1 for r in rs if r["error"])
            lat = sorted(r["latency_s"] for r in rs)
            p50 = lat[len(lat) // 2] if lat else "-"
            lines.append(
                f"| {src} | {kind} | {len(rs)} | {hits} | {hits / max(len(rs), 1):.1%} "
                f"| {title_only / max(len(rs), 1):.1%} | {errs} | {p50} |"
            )
            if len(recs) >= 0.95 * len(sampled_refs()):  # the union counts only sources that completed
                for k in keys:
                    union[kind][k] = union[kind].get(k, False) or (k in recs and hit(recs[k]))
                    loose[kind][k] = loose[kind].get(k, False) or (k in recs and hit(recs[k], strict_year=False))
        u = union[kind]
        rate = sum(u.values()) / max(len(u), 1)
        lo = loose[kind]
        lines.append(
            f"| **union of completed sources** | {kind} | {len(u)} | {sum(u.values())} | {rate:.1%} "
            f"| {sum(lo.values()) / max(len(lo), 1):.1%} | | |"
        )
    print("\n".join(lines))
    misses = [k for k, v in union["parent"].items() if not v]
    title_of = {key(r["title"]): r["title"] for s in sample for r in s["refs"]}
    (CACHE / "parent_misses.txt").write_text("\n".join(title_of[k] for k in misses), encoding="utf-8")
    gmiss = [k for k, v in union["generated"].items() if not v]
    (CACHE / "generated_misses.txt").write_text("\n".join(title_of[k] for k in gmiss), encoding="utf-8")
    print(f"\nmisses by every completed source: parent {len(misses)} (parent_misses.txt), generated {len(gmiss)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--source", choices=sorted(SOURCES))
    ap.add_argument("--max-seconds", type=float, default=540)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare()
    elif a.source:
        run_source(a.source, a.max_seconds)
    elif a.report:
        report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

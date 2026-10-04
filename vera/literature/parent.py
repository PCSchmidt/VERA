"""Parent-problem selection (RSH-F-10): which method paper's code could an empirical question be tested on?

For an empirical question the stage looks in the papers it read for repositories, checks each live, has the model
read the evidence for the facts a program cannot get (datasets, compute), and picks one, or says why none fits.

    parent ─► parent_gate

`parent` is the producer. Repository URLs are found in the papers' PDFs by a regular expression (text and link
annotations), never taken from model text; each is looked up on GitHub (resolves, licence, last push, archived) and
matched against the Dockerfiles in `docker/`. The model only fills what the papers say: whether the paper presents the
repository as its own code, the datasets, the compute (stated, or inferred and marked so), and a minutes-per-replication
estimate. `parent_gate` orders the candidates by deterministic checks, then asks the judge path `lit.parent_fits` about
up to `MAX_JUDGED` of them and picks the first the judge confidently accepts that also passes the checks. Finding
no candidate is a valid outcome that sends the run on as a non-empirical paper, with the reasons recorded.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path

import httpx

from vera.literature import parent_questions as questions
from vera.literature.deps import LitDeps
from vera.literature.retrieval import HttpCache
from vera.literature.stages import _confirmed_question
from vera.loop.stages import _extract_json, _stop, _write_json, ask_gate, stage_result
from vera.schemas import ParentCandidate, ParentSelection, Verdict

HOST = r"github\.com"
REPO = re.compile(rf"https?://(?:www\.)?{HOST}/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)*)")
NOT_REPOS = {"features", "topics", "orgs", "sponsors", "marketplace", "settings", "about", "pricing", "login"}
MAX_PAPERS = 12  # papers whose PDFs are searched for repositories
MAX_REPOS = 8  # repositories assessed
MAX_JUDGED = 3  # candidates the judge is asked about
FITS_MINUTES = 30.0  # a replication longer than this on CPU does not fit the loop's limits
SYSTEM = (
    "You read research papers and report only what they say. When a fact is not in the evidence you say it is "
    "unknown; you never guess a repository, a dataset or a licence."
)


# ── finding and checking repositories ────────────────────────────────────────────────────────────────


def pdf_text_and_links(pdf: bytes) -> tuple[str, list[str]]:
    """The PDF's text and its link annotations (a footnote URL is often only a link)."""
    import pymupdf  # noqa: PLC0415 - heavy import, only this stage needs it

    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
        links = [lk.get("uri", "") for page in doc for lk in page.get_links() if lk.get("uri")]
    return text, links


def normalize(owner: str, name: str) -> str:
    name = re.sub(r"\.git$", "", name).rstrip(".")
    return f"https://github.com/{owner}/{name}"


def find_repos(text: str, links: list[str]) -> list[dict]:
    """Repositories named in a paper: {url, context}, in order of first mention. Line-broken URLs are rejoined."""
    text = re.sub(r"(https?://\S*?[/\-_.])\s*\n\s*(?=[A-Za-z0-9])", r"\1", text)
    flat = " ".join(text.split())
    found: dict[str, str] = {}
    for m in REPO.finditer(flat):
        owner, name = m.group(1), m.group(2)
        if owner.lower() in NOT_REPOS:
            continue
        url = normalize(owner, name)
        if url.lower() in {u.lower() for u in found}:
            continue
        start = max(flat.rfind(". ", 0, m.start()) + 2, m.start() - 300)
        end = flat.find(" ", m.end() + 160)
        found[url] = flat[start : end if end != -1 else len(flat)].strip()
    for link in links:
        m = REPO.match(link)
        if m and m.group(1).lower() not in NOT_REPOS:
            url = normalize(m.group(1), m.group(2))
            if url.lower() not in {u.lower() for u in found}:
                found[url] = "(a link in the paper's PDF)"
    return [{"url": u, "context": c} for u, c in found.items()]


EVIDENCE = re.compile(
    r"data ?sets?|benchmark|\bUCI\b|OpenML|Kaggle|\bCPU\b|\bGPU\b|run ?time|seconds|minutes|hours|"
    r"computational (?:cost|budget)|experiments? (?:on|with|use)",
    re.IGNORECASE,
)
NAMED_DATASET = re.compile(r"\b[A-Z][A-Za-z\-]+(?: [A-Z][A-Za-z\-]+)* [Dd]ata ?sets?\b|[Aa]dditional datasets")
TABLE_ROW = re.compile(r"(?:\b[A-Z][a-z]+(?: [A-Z][a-z]+)? \d{3,6} \d{1,3}\b.*?){3,}")
GENERIC = re.compile(r"training data ?set|new data ?set|a given realization", re.IGNORECASE)


def evidence_excerpt(text: str, limit: int = 1800) -> str:
    """The sentences of the paper's text that most speak of named datasets and compute, in document order.

    A sentence scores for each datasets-or-compute keyword, more for a named dataset ("the California Housing dataset")
    or a table of dataset sizes, and less for a generic "training dataset"; the best are kept up to `limit` chars."""
    flat = " ".join(re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text).split())
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat)
    scored = []
    for i, sentence in enumerate(sentences):
        if not 25 <= len(sentence) <= 900 or not (EVIDENCE.search(sentence) or TABLE_ROW.search(sentence)):
            continue
        score = len(EVIDENCE.findall(sentence)) + 3 * bool(NAMED_DATASET.search(sentence))
        score += 4 * bool(TABLE_ROW.search(sentence)) - 2 * bool(GENERIC.search(sentence))
        scored.append((score, i, sentence[:600]))
    keep, size = [], 0
    for score, i, sentence in sorted(scored, key=lambda t: (-t[0], t[1])):
        if score <= 0 or size + len(sentence) > limit:
            continue
        keep.append((i, sentence))
        size += len(sentence) + 1
    return " ".join(s for _, s in sorted(keep))


class RepoLookup:
    """GitHub's repository metadata, cached by URL with the date. A GITHUB_TOKEN is optional."""

    def __init__(self, cache: HttpCache, client: httpx.Client | None = None) -> None:
        self.cache = cache
        headers = {"User-Agent": "VERA-research/0.1", "Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        self.client = client or httpx.Client(timeout=30, headers=headers, follow_redirects=True)

    def __call__(self, repo_url: str) -> dict:
        owner, name = repo_url.removeprefix("https://github.com/").split("/", 1)
        api = f"https://api.github.com/repos/{owner}/{name}"
        cached = self.cache.get(api, {})
        if cached:
            status, body = cached["text"].split("\n", 1)
        else:
            resp = self.client.get(api)
            status, body = str(resp.status_code), resp.text
            if resp.status_code in (200, 404):
                self.cache.put(api, {}, f"{status}\n{body}")
        if status != "200":
            return {"resolves": False}
        data = json.loads(body)
        lic = (data.get("license") or {}).get("spdx_id")
        return {"resolves": True, "licence": None if lic in (None, "NOASSERTION") else lic,
                "pushed_at": data.get("pushed_at"), "archived": bool(data.get("archived")),
                "description": data.get("description") or ""}  # fmt: skip


def harness_for(repo_url: str, root: Path) -> str | None:
    """The `docker/` directory whose Dockerfile builds this repository (it names the repository's URL), if any."""
    needle = repo_url.lower().removeprefix("https://")
    for dockerfile in sorted((root / "docker").glob("*/Dockerfile")):
        if needle in dockerfile.read_text(encoding="utf-8").lower():
            return dockerfile.parent.relative_to(root).as_posix()
    return None


# ── the model's reading ──────────────────────────────────────────────────────────────────────────────


def assess_prompt(question: str, items: list[dict]) -> str:
    blocks = []
    for i, it in enumerate(items):
        blocks.append(
            f"[{i}] Paper: {it['title']} ({it['paper_id']})\nRepository named in it: {it['repo_url']}\n"
            f"Sentence naming it: {it['url_context']}\nAbstract: {it['abstract'][:1400]}\n"
            f"Sentences of the paper that mention datasets or compute: {it.get('excerpt') or '(none found)'}"
        )
    return (
        f"Research question (to be tested with small CPU experiments): {question}\n\n"
        "For each paper below, report what the paper itself says, as a JSON list with one object per paper:\n"
        '{"index": n, "own_code": "yes"|"no"|"unclear", "datasets": [names of public datasets it uses, '
        "[] if none stated in the abstract or the sentences given], "
        '"compute": "what the method needs to run, in a short phrase", '
        '"compute_basis": "stated"|"inferred"|"unknown", "cpu_minutes": minutes for one replication of its '
        'baseline on a laptop CPU, or null if you cannot tell, "notes": "one sentence"}\n'
        '"own_code" is "yes" only if the sentence presents the repository as this paper\'s own code (not a baseline '
        'or a library it uses). Use "inferred" for compute only when the paper states none and you infer it from the '
        'method and datasets; otherwise "unknown". Output only the JSON list.\n\n' + "\n\n".join(blocks)
    )


def parse_assessments(reply: str, n: int) -> dict[int, dict]:
    data = _extract_json(reply, "[", "]")
    out: dict[int, dict] = {}
    for obj in data if isinstance(data, list) else []:
        if isinstance(obj, dict) and isinstance(obj.get("index"), int) and 0 <= obj["index"] < n:
            out[obj["index"]] = obj
    return out


def build_candidate(item: dict, meta: dict, assessed: dict | None, root: Path) -> ParentCandidate:
    a = assessed or {}
    minutes = a.get("cpu_minutes")
    basis = a.get("compute_basis")
    return ParentCandidate(
        source_key=item["key"], paper_id=item["paper_id"], title=item["title"], repo_url=item["repo_url"],
        repo_resolves=bool(meta.get("resolves")), licence=meta.get("licence"), pushed_at=meta.get("pushed_at"),
        archived=bool(meta.get("archived")),
        own_code=a.get("own_code") if a.get("own_code") in ("yes", "no") else "unclear",
        url_context=item["url_context"][:400], datasets=[str(d) for d in a.get("datasets", []) if d][:8],
        compute=str(a.get("compute", ""))[:200], compute_basis=basis if basis in ("stated", "inferred") else "unknown",
        cpu_minutes=float(minutes) if isinstance(minutes, int | float) and not isinstance(minutes, bool) else None,
        harness_in_docker=harness_for(item["repo_url"], root), notes=str(a.get("notes", ""))[:300],
    )  # fmt: skip


def problems(c: ParentCandidate) -> list[str]:
    """Deterministic reasons a candidate cannot be a parent."""
    out = []
    if not c.repo_resolves:
        out.append("the repository does not resolve")
    if c.licence is None:
        out.append("no licence recorded by the host")
    if c.archived:
        out.append("the repository is archived")
    if c.own_code == "no":
        out.append("the paper does not present it as its own code")
    if c.cpu_minutes is not None and c.cpu_minutes > FITS_MINUTES:
        out.append(f"one replication is estimated at {c.cpu_minutes:g} minutes on CPU (limit {FITS_MINUTES:g})")
    if not c.datasets:
        out.append("no public dataset identified")
    return out


def order(cands: list[ParentCandidate]) -> list[ParentCandidate]:
    """Best first: fewest problems, then the paper's own code, then an existing harness, then the shortest runtime."""
    return sorted(cands, key=lambda c: (len(problems(c)), c.own_code != "yes", c.harness_in_docker is None,
                                        c.cpu_minutes if c.cpu_minutes is not None else 1e9))  # fmt: skip


# ── nodes ────────────────────────────────────────────────────────────────────────────────────────────


def _records(deps: LitDeps) -> dict[str, dict]:
    path = deps.run_dir / "retrieved.jsonl"
    return {r["key"]: r for r in (json.loads(ln) for ln in path.read_text("utf-8").splitlines() if ln)}


def parent_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        if not json.loads((deps.run_dir / "scope.json").read_text(encoding="utf-8")).get("empirical"):
            return {"parent_candidates": [], "trail": ["parent"]}  # no parent problem is needed
        records = _records(deps)
        fetch, lookup = deps.extra["fetch_pdf"], deps.extra["repo_lookup"]
        root = Path(deps.extra.get("root", Path.cwd()))
        order_keys = [e["key"] for e in sorted(state.get("read_report", []), key=lambda e: e["mode"] != "fulltext")]
        items: list[dict] = []
        scanned: list[dict] = []
        for key in order_keys[:MAX_PAPERS]:
            rec = records[key]
            if not rec.get("pdf_url"):
                scanned.append({"key": key, "repos": 0, "note": "no PDF"})
                continue
            try:
                pdf = fetch(rec["pdf_url"])
                text, links = pdf_text_and_links(pdf) if pdf else ("", [])
            except Exception as exc:  # noqa: BLE001 - one unreadable PDF must not stop the search
                scanned.append({"key": key, "repos": 0, "note": f"{type(exc).__name__}: {str(exc)[:100]}"})
                continue
            repos = find_repos(text, links)
            excerpt = evidence_excerpt(text) if repos else ""
            scanned.append({"key": key, "repos": len(repos)})
            seen = {i["repo_url"].lower() for i in items}
            items += [{"key": key, "paper_id": rec["id"], "title": rec["title"], "repo_url": r["url"],
                       "url_context": r["context"], "abstract": rec.get("abstract") or "", "excerpt": excerpt}
                      for r in repos if r["url"].lower() not in seen]  # fmt: skip
        items = items[:MAX_REPOS]
        assessed: dict[int, dict] = {}
        if items:
            reply = deps.generator.generate(SYSTEM, assess_prompt(question, items), component="p3.parent")
            assessed = parse_assessments(reply, len(items))
        candidates = [build_candidate(it, lookup(it["repo_url"]), assessed.get(i), root) for i, it in enumerate(items)]
        artifact = _write_json(deps, "parent_candidates", {
            "papers_scanned": scanned, "candidates": [c.model_dump(mode="json") for c in candidates]})  # fmt: skip
        return {"parent_candidates": [c.model_dump(mode="json") for c in candidates],
                "artifacts": {"parent_candidates": artifact}, "trail": ["parent"]}  # fmt: skip

    return node


def parent_gate_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question = _confirmed_question(deps)
        scope = json.loads((deps.run_dir / "scope.json").read_text(encoding="utf-8"))
        candidates = order([ParentCandidate.model_validate(c) for c in state.get("parent_candidates", [])])
        verdicts: list[Verdict] = []
        picked, reasons = None, []
        empirical = bool(scope.get("empirical"))
        if empirical:
            if not candidates:
                reasons.append("no repository was named in the papers read")
            for c in candidates[:MAX_JUDGED]:
                bad = problems(c)
                if bad:
                    reasons.append(f"{c.repo_url}: {'; '.join(bad)}")
                    continue
                q, material = questions.parent_fits(question, c)
                v, confident = ask_gate(deps, "parent", q, material, None, state)
                verdicts.append(v)
                if confident and v.answer is True:
                    picked = c.repo_url
                    break
                reasons.append(f"{c.repo_url}: the judge {'did not accept it' if confident else 'was not confident'}")
            for c in candidates[MAX_JUDGED:]:
                why = "; ".join(problems(c)) or f"ranked below the top {MAX_JUDGED}"
                reasons.append(f"{c.repo_url}: not assessed ({why})")
        else:
            reasons.append("the confirmed question is not empirical, so no parent problem is needed")
        refusal_ok = True
        if empirical and picked is None:  # a refusal is itself checked: is it right that nothing fits?
            q, material = questions.parent_refusal(question, candidates, reasons)
            v, confident = ask_gate(deps, "parent", q, material, None, state)
            verdicts.append(v)
            refusal_ok = confident and v.answer is True
        selection = ParentSelection(
            run_id=deps.spec.run_id, topic_id=deps.spec.topic.id, question=question, candidates=candidates,
            picked=picked, none_fits_reason=None if picked else "; ".join(reasons), verdicts=verdicts,
        )  # fmt: skip
        (deps.run_dir / "parent.json").write_text(selection.model_dump_json(indent=1), encoding="utf-8")
        update: dict = {"artifacts": {"parent": "parent.json"}, "trail": ["parent_gate"], "parent": picked}
        if not empirical:
            return update  # nothing was decided: no verdict, no stage result
        metrics = {"n_candidates": float(len(candidates)), "n_judged": float(len(verdicts)),
                   "picked": 1.0 if picked else 0.0}  # fmt: skip
        why = None if refusal_ok else "the judge did not confirm that no candidate fits"
        sr = stage_result(deps, "parent", "parent.json", verdicts, "accept" if refusal_ok else "reject", metrics,
                          reason=why)  # fmt: skip
        update["stage_results"] = [sr]
        if not refusal_ok:
            update |= _stop("parent", f"gate: {why}")
        return update

    return node

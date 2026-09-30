"""Benchmark items labelled by construction (Increment 1; risk R3; docs/03 `BenchmarkItem`).

Three tasks, each built so the correct answer follows from how the item was
made, and always computed from the material the judge is shown:

- loop_gate: generated TreeHFD-style result tables (the Increment 2 problem)
  with near-ties, exact ties, mixed metric directions and a distractor
  method. "Does candidate X beat the baseline?" (Boolean), "which method is
  best?" (Choice), "how many candidates beat it?" (Score). Labels are read
  back from the rendered numbers, so rounding can't make a label wrong.
- numeric: a claim about one cell of a table Docling extracted from a corpus
  paper (T3), either exact or perturbed (digit change, decimal shift, value
  swapped in from another cell). Boolean per claim; Score = how many of three
  claims hold.
- citation: "does this reference list contain an entry for paper X?" over a
  window of a GROBID reference list (T3). Negatives are near misses: a
  similar title from another paper's references, a title with one meaning
  word swapped, and a few unrelated titles.

Everything is deterministic given the seed. Splitting, hashing and file
output live in scripts/build_benchmark.py.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from vera.schemas import BenchmarkItem, Question, QuestionType

GENERATOR = "vera.bench.build 0.1"

# ── loop_gate ─────────────────────────────────────────────────────────────────

BASELINE = "TreeHFD (baseline)"
DISTRACTOR = "TreeSHAP"
CANDIDATES = ["C1: coupled grids", "C2: shared knots", "C3: ridge-smoothed leaves", "C4: pruned interactions"]
DATASETS = ["Abalone", "Airfoil", "Bike Sharing", "Housing", "Concrete", "Nutrition", "Parkinson", "Power Plant"]


@dataclass(frozen=True)
class Metric:
    name: str
    lower_is_better: bool
    lo: float  # baseline values are drawn log-uniformly from [lo, hi]
    hi: float
    sig: int  # significant figures shown

    @property
    def arrow(self) -> str:
        return "↓" if self.lower_is_better else "↑"

    def better(self, a: float, b: float) -> bool:
        return a < b if self.lower_is_better else a > b


METRICS = [
    Metric("Residual MSE", True, 0.002, 0.08, 3),
    Metric("Cumulated MSE", True, 0.1, 2.0, 3),
    Metric("Local variability", True, 0.01, 0.5, 3),
    Metric("Explained variance (%)", False, 20.0, 97.0, 3),
    Metric("Orthogonality", True, 1e-4, 0.05, 2),
    Metric("Runtime (s)", True, 1.0, 300.0, 3),
]

# relation of a candidate's mean to the baseline's, as relative change in the "better" direction
RELATIONS = {
    "clear_win": (0.05, 0.40),
    "near_win": (0.004, 0.012),
    "tie": (0.0, 0.0),
    "near_loss": (-0.012, -0.004),
    "clear_loss": (-0.40, -0.05),
}
RELATION_WEIGHTS = {"clear_win": 0.2, "near_win": 0.25, "tie": 0.1, "near_loss": 0.25, "clear_loss": 0.2}


def fmt_sig(x: float, sig: int) -> str:
    """x to `sig` significant figures, fixed-point (no exponent), keeping trailing zeros."""
    if x == 0:
        return "0"
    digits = max(sig - 1 - int(f"{abs(x):e}".split("e")[1]), 0)
    return f"{x:.{digits}f}"


@dataclass
class ResultTable:
    methods: list[str]
    columns: list[tuple[str, Metric]]  # (dataset, metric)
    means: dict[tuple[str, int], float]  # (method, column index) -> mean as rendered
    text: str
    relations: dict[tuple[str, int], str] = field(default_factory=dict)


def _perturb_mean(rng: random.Random, base: float, metric: Metric, relation: str) -> float:
    lo, hi = RELATIONS[relation]
    delta = rng.uniform(lo, hi)
    # "better" means lower for lower-is-better metrics
    return base * (1 - delta) if metric.lower_is_better else base * (1 + delta)


def result_table(rng: random.Random) -> ResultTable:
    datasets = rng.sample(DATASETS, 2)
    metrics = rng.sample(METRICS, 2)
    columns = [(d, m) for d in datasets for m in metrics]
    candidates = rng.sample(CANDIDATES, 3)
    methods = [BASELINE, DISTRACTOR, *candidates]
    rng.shuffle(methods)  # the baseline is not always the first row
    rendered: dict[tuple[str, int], tuple[str, str]] = {}
    relations: dict[tuple[str, int], str] = {}
    for j, (_, metric) in enumerate(columns):
        base = metric.lo * (metric.hi / metric.lo) ** rng.random()
        if metric.name == "Explained variance (%)":
            base = min(base, 90.0)
        base_s = fmt_sig(base, metric.sig + 1)
        rendered[(BASELINE, j)] = (base_s, fmt_sig(base * rng.uniform(0.02, 0.15), 2))
        for method in methods:
            if method == BASELINE:
                continue
            relation = rng.choices(list(RELATION_WEIGHTS), weights=list(RELATION_WEIGHTS.values()))[0]
            relations[(method, j)] = relation
            mean_s = base_s if relation == "tie" else fmt_sig(_perturb_mean(rng, float(base_s), metric, relation), 4)
            # spread sometimes dwarfs the gap: the question says to ignore it
            rendered[(method, j)] = (mean_s, fmt_sig(float(mean_s) * rng.uniform(0.02, 0.3), 2))
    header = ["Method"] + [f"{d} · {m.name} {m.arrow}" for d, m in columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for method in methods:
        cells = [f"{rendered[(method, j)][0]} ± {rendered[(method, j)][1]}" for j in range(len(columns))]
        lines.append("| " + " | ".join([method, *cells]) + " |")
    text = (
        "Results from a research-loop run on the TreeHFD problem (mean ± std over 5 seeds). "
        "↓ = lower is better; ↑ = higher is better.\n\n" + "\n".join(lines)
    )
    means = {k: float(v[0]) for k, v in rendered.items()}
    return ResultTable(methods, columns, means, text, relations)


def _beats(table: ResultTable, method: str, j: int) -> bool:
    _, metric = table.columns[j]
    return metric.better(table.means[(method, j)], table.means[(BASELINE, j)])


def loop_items(rng: random.Random, n_tables: int, seed: int) -> list[tuple[int, BenchmarkItem]]:
    """(table index, item) pairs; the table index is the split unit."""
    out: list[tuple[int, BenchmarkItem]] = []
    for t in range(n_tables):
        table = result_table(rng)
        candidates = [m for m in table.methods if m.startswith("C")]
        cols = list(range(len(table.columns)))
        rng.shuffle(cols)
        # Boolean: beats baseline? (two per table for the first quarter of tables)
        for j in cols[: 2 if t < n_tables // 4 else 1]:
            # aim for balanced labels: prefer a candidate whose answer matches a coin flip
            want = rng.random() < 0.5
            matching = [c for c in candidates if _beats(table, c, j) == want]
            method = rng.choice(matching or candidates)
            dataset, metric = table.columns[j]
            direction = "lower" if metric.lower_is_better else "higher"
            q = Question(
                id="loop.beats_baseline",
                type=QuestionType.BOOLEAN,
                text=(
                    f'Does "{method}" beat the TreeHFD baseline on {metric.name} for the {dataset} dataset? '
                    f"It beats it only if its mean is strictly better ({direction} "
                    "is better for this metric); ignore the ± spread."
                ),
            )
            kind = table.relations[(method, j)]
            out.append((t, _item(q, table.text, _beats(table, method, j), "loop_gate", kind, f"table{t}", seed)))
        # Choice: best method on one column (must be unique)
        j = cols[-1]
        dataset, metric = table.columns[j]
        values = {m: table.means[(m, j)] for m in table.methods}
        best = min(values, key=values.get) if metric.lower_is_better else max(values, key=values.get)
        if sum(v == values[best] for v in values.values()) == 1:
            q = Question(
                id="loop.best_method",
                type=QuestionType.CHOICE,
                text=f"Which method has the best mean {metric.name} on the {dataset} dataset? Ignore the ± spread.",
                options=list(table.methods),
            )
            out.append((t, _item(q, table.text, best, "loop_gate", "best_of_5", f"table{t}", seed)))
        # Score: how many candidates beat the baseline on one column
        if t < (3 * n_tables) // 4:
            j = cols[0]
            dataset, metric = table.columns[j]
            count = sum(_beats(table, c, j) for c in candidates)
            q = Question(
                id="loop.count_beating",
                type=QuestionType.SCORE,
                text=(
                    f"How many of the candidate methods ({', '.join(sorted(candidates))}) beat the TreeHFD baseline "
                    f"on {metric.name} for the {dataset} dataset? A candidate beats it only if its mean is strictly "
                    "better; ignore the ± spread. TreeSHAP is not a candidate."
                ),
                scale=(0, 3),
            )
            out.append((t, _item(q, table.text, count, "loop_gate", "count", f"table{t}", seed)))
    return out


# ── numeric ───────────────────────────────────────────────────────────────────

MARKS = re.compile(r"\*\*|[*∗†‡§¶↑↓]|\\\*")
NUMBER = re.compile(
    r"^(?P<num>[-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−]?\d+(?:\.\d+)?)(?P<pct>%?)(?P<rest>\s*(?:±|\+/-).*)?$"
)


@dataclass
class ParsedTable:
    caption: str
    header: list[str]
    rows: list[list[str]]
    text: str  # as the judge sees it: caption + Markdown


def parse_docling_tables(md: str) -> list[ParsedTable]:
    """The tables in a docling_tables.md file (t3_parse.py output) that parse as rectangular Markdown."""
    tables = []
    for section in re.split(r"^## Table \d+\s*$", md, flags=re.M)[1:]:
        caption_match = re.search(r"<!-- caption: (.*?) -->", section, re.S)
        caption = caption_match.group(1).strip() if caption_match else ""
        lines = [ln.strip() for ln in section.splitlines() if ln.strip().startswith("|")]
        if len(lines) < 4 or not re.fullmatch(r"\|[\s|:-]+\|", lines[1]):
            continue
        cells = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
        width = len(cells[0])
        if any(len(r) != width for r in cells) or width < 3:
            continue
        header, rows = cells[0], cells[2:]
        compact = "\n".join("| " + " | ".join(r) + " |" for r in [header, ["---"] * width, *rows])
        text = (f"Table caption: {caption}\n\n" if caption else "") + compact
        tables.append(ParsedTable(caption, header, rows, text))
    return tables


def cell_number(cell: str) -> tuple[str, float] | None:
    """The one number a cell reports (ignoring marks and any ± term), as shown and as a float."""
    clean = " ".join(MARKS.sub("", cell).split())
    m = NUMBER.match(clean)
    if not m:
        return None
    shown = m.group("num").replace("−", "-") + m.group("pct")
    return shown, float(m.group("num").replace(",", "").replace("−", "-"))


def _unique_nonnumeric(labels: list[str]) -> list[bool]:
    ok = [bool(s) and len(s) <= 60 and cell_number(s) is None and "<br>" not in s and "&" not in s for s in labels]
    return [o and labels.count(s) == 1 for o, s in zip(ok, labels, strict=True)]


def eligible_cells(table: ParsedTable) -> list[tuple[int, int, str, float]]:
    """(row, col, shown, value) for cells a claim can name unambiguously.

    A table with a cell holding three or more numbers is skipped: that is the
    signature of rows Docling merged into one, where row labels don't line up.
    """
    if any(len(re.findall(r"\d+(?:\.\d+)?", c)) >= 3 for r in table.rows for c in r[1:]):
        return []
    col_ok = _unique_nonnumeric(table.header)
    row_ok = _unique_nonnumeric([r[0] for r in table.rows])
    out = []
    for i, row in enumerate(table.rows):
        for j in range(1, len(row)):
            if row_ok[i] and col_ok[j]:
                parsed = cell_number(row[j])
                if parsed:
                    out.append((i, j, *parsed))
    return out


def _digit_change(rng: random.Random, shown: str) -> str | None:
    positions = [k for k, ch in enumerate(shown) if ch.isdigit()]
    lead = next((k for k in positions if shown[k] != "0"), None)
    choices = [k for k in positions if k != lead]
    if not choices:
        return None
    k = rng.choice(choices)
    new = rng.choice([d for d in "0123456789" if d != shown[k]])
    return shown[:k] + new + shown[k + 1 :]


def _decimal_shift(rng: random.Random, shown: str) -> str | None:
    pct = "%" if shown.endswith("%") else ""
    body = shown.rstrip("%").replace(",", "")
    neg = body.startswith("-")
    body = body.lstrip("-")
    if "." not in body and len(body) < 2:
        return None
    ip, _, fp = body.partition(".")
    digits, point = ip + fp, len(ip)
    point += rng.choice([-1, 1])
    if point <= 0:
        digits, point = "0" * (1 - point) + digits, 1
    if point >= len(digits):
        digits = digits + "0" * (point - len(digits))
        new = digits
    else:
        new = digits[:point] + "." + digits[point:]
    new = new.lstrip("0") or "0"
    if new.startswith("."):
        new = "0" + new
    return ("-" if neg else "") + new + pct


def perturb(rng: random.Random, table: ParsedTable, cell: tuple[int, int, str, float]) -> tuple[str, str] | None:
    """A wrong value for the cell and the perturbation kind, or None if none applies."""
    i, j, shown, value = cell
    kinds = ["digit_change", "decimal_shift", "cell_swap"]
    rng.shuffle(kinds)
    for kind in kinds:
        if kind == "digit_change":
            new = _digit_change(rng, shown)
        elif kind == "decimal_shift":
            new = _decimal_shift(rng, shown)
        else:
            others = [c for c in eligible_cells(table) if c[3] != value and (c[0] == i or c[1] == j)]
            new = rng.choice(others)[2] if others else None
        if new is not None and cell_number(new) and cell_number(new)[1] != value:
            return new, kind
    return None


def _claim(table: ParsedTable, i: int, j: int, value: str) -> str:
    return f'the value in row "{table.rows[i][0]}", column "{table.header[j]}" is {value}'


NUMERIC_NOTE = " Ignore any ± term and formatting marks such as bold or asterisks; the value must match as written."


def numeric_items(
    rng: random.Random, tables_by_paper: dict[str, list[ParsedTable]], n_bool: int, n_score: int, seed: int
) -> list[tuple[str, BenchmarkItem]]:
    """(paper, item) pairs; the paper is the split unit."""
    pool = [
        (paper, t, cells)
        for paper, tables in sorted(tables_by_paper.items())
        for t in tables
        if len(t.text) <= 5000 and len(cells := eligible_cells(t)) >= 4
    ]
    papers = sorted({p for p, _, _ in pool})
    out: list[tuple[str, BenchmarkItem]] = []
    used: set[tuple[int, int, int]] = set()

    def draw(paper: str) -> tuple[ParsedTable, tuple[int, int, str, float]] | None:
        options = [(k, t, c) for k, (p, t, cs) in enumerate(pool) if p == paper for c in cs]
        options = [(k, t, c) for k, t, c in options if (k, c[0], c[1]) not in used]
        if not options:
            return None
        k, t, c = rng.choice(options)
        used.add((k, c[0], c[1]))
        return t, c

    b = 0
    while b < n_bool:
        paper = papers[b % len(papers)]
        drawn = draw(paper)
        if drawn is None:
            papers.remove(paper)
            continue
        table, cell = drawn
        truth = rng.random() < 0.5
        wrong = None if truth else perturb(rng, table, cell)
        if not truth and wrong is None:
            continue
        value, kind = (cell[2], "true") if truth else wrong
        q = Question(
            id="num.claim_consistent",
            type=QuestionType.BOOLEAN,
            text=f"Is this claim consistent with the table? Claim: {_claim(table, cell[0], cell[1], value)}."
            + NUMERIC_NOTE,
        )
        out.append((paper, _item(q, table.text, truth, "numeric", kind, paper, seed)))
        b += 1
    s = 0
    by_table = [(p, t, cs) for p, t, cs in pool if len(cs) >= 6]
    while s < n_score and by_table:
        paper, table, cells = by_table[s % len(by_table)]
        picks = rng.sample(cells, 3)
        claims, count, kinds = [], 0, []
        for cell in picks:
            truth = rng.random() < 0.5
            wrong = None if truth else perturb(rng, table, cell)
            truth = truth or wrong is None
            count += truth
            kinds.append("true" if truth else wrong[1])
            claims.append(_claim(table, cell[0], cell[1], cell[2] if truth else wrong[0]))
        q = Question(
            id="num.count_consistent",
            type=QuestionType.SCORE,
            text="How many of these three claims are consistent with the table? "
            + " ".join(f"({n}) {c[0].upper() + c[1:]}." for n, c in enumerate(claims, 1))
            + NUMERIC_NOTE,
            scale=(0, 3),
        )
        out.append((paper, _item(q, table.text, count, "numeric", "+".join(kinds), paper, seed)))
        s += 1
    return out


# ── citation ──────────────────────────────────────────────────────────────────

VENUE_WORDS = re.compile(r"\b(proceedings|conference|journal|arxiv|preprint|workshop|transactions)\b", re.I)
SWAPS = {
    "linear": "nonlinear", "nonlinear": "linear", "convex": "nonconvex", "nonconvex": "convex",
    "supervised": "unsupervised", "unsupervised": "supervised", "online": "offline", "offline": "online",
    "sparse": "dense", "dense": "sparse", "graph": "hypergraph", "graphs": "hypergraphs",
    "discrete": "continuous", "continuous": "discrete", "stochastic": "deterministic",
    "deterministic": "stochastic", "local": "global", "global": "local", "single": "multiple",
    "multi-agent": "single-agent", "robust": "fragile", "bayesian": "frequentist", "causal": "associative",
    "private": "public", "federated": "centralized", "centralized": "federated", "explicit": "implicit",
    "implicit": "explicit", "adversarial": "cooperative", "forward": "backward", "backward": "forward",
    "first-order": "second-order", "second-order": "first-order", "low-rank": "full-rank", "large": "small",
    "small": "large", "deep": "shallow", "fast": "slow", "optimal": "suboptimal", "exact": "approximate",
}  # fmt: skip


def norm_title(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def usable_title(title: str) -> bool:
    words = title.split()
    return 4 <= len(words) <= 25 and not VENUE_WORDS.search(title)


def _tokens(title: str) -> set[str]:
    return {w for w in norm_title(title).split() if len(w) > 3}


def _distinct(title: str, window: list[dict], all_norm: set[str] | None = None) -> bool:
    """True if `title` names no entry in the window (not equal, not contained, not a near-duplicate)."""
    n = norm_title(title)
    for e in window:
        en, et = norm_title(e["title"]), norm_title(e["text"])
        if n == en or n in et or SequenceMatcher(None, n, en).ratio() >= 0.9:
            return False
    return all_norm is None or n not in all_norm


def swap_word(rng: random.Random, title: str) -> str | None:
    words = title.split()
    spots = [k for k, w in enumerate(words) if w.lower().strip(",:;") in SWAPS]
    if not spots:
        return None
    k = rng.choice(spots)
    core = words[k].strip(",:;")
    new = SWAPS[core.lower()]
    new = new.capitalize() if core[0].isupper() else new
    words[k] = words[k].replace(core, new)
    return " ".join(words)


CITATION_KINDS = {"true": 0.5, "near_miss_title": 0.25, "word_swap": 0.15, "unrelated": 0.10}


def citation_items(
    rng: random.Random, refs_by_paper: dict[str, list[dict]], papers: list[str], per_paper: int, window: int, seed: int
) -> list[tuple[str, BenchmarkItem]]:
    """(paper, item) pairs from reference-list windows; the paper is the split unit."""
    all_titles = [
        (p, e["title"]) for p, refs in sorted(refs_by_paper.items()) for e in refs if usable_title(e["title"])
    ]
    all_norm = {norm_title(t) for _, t in all_titles}
    out: list[tuple[str, BenchmarkItem]] = []
    for paper in papers:
        refs = refs_by_paper[paper]
        made = 0
        tries = 0
        while made < per_paper and tries < 50:
            tries += 1
            start = rng.randrange(max(1, len(refs) - window + 1))
            shown = refs[start : start + window]
            titles = [e for e in shown if usable_title(e["title"])]
            if len(titles) < 5:
                continue
            kind = rng.choices(list(CITATION_KINDS), weights=list(CITATION_KINDS.values()))[0]
            if kind == "true":
                target = rng.choice(titles)["title"]
            elif kind == "near_miss_title":
                window_tokens = [_tokens(e["title"]) for e in titles]

                def overlap(t: str, window_tokens: list[set[str]] = window_tokens) -> float:
                    tk = _tokens(t)
                    return max(len(tk & w) / (len(tk | w) or 1) for w in window_tokens)

                # rank by cheap token overlap first; the costly distinctness check runs on the top only
                ranked = sorted((t for p, t in all_titles if p != paper), key=overlap, reverse=True)[:40]
                ranked = [t for t in ranked if _distinct(t, shown)][:10]
                if not ranked:
                    continue
                target = rng.choice(ranked)
                if overlap(target) < 0.15:
                    continue
            elif kind == "word_swap":
                swapped = [s for e in titles if (s := swap_word(rng, e["title"])) and _distinct(s, shown, all_norm)]
                if not swapped:
                    continue
                target = rng.choice(swapped)
            else:
                target = rng.choice([t for p, t in all_titles if p != paper])
                if not _distinct(target, shown):
                    continue
            listing = "\n".join(f"[{e['n']}] {e['text']}" for e in shown)
            state = f"Reference list (entries {shown[0]['n']}–{shown[-1]['n']} of a paper's bibliography):\n\n{listing}"
            q = Question(
                id="cite.contains_entry",
                type=QuestionType.BOOLEAN,
                text=f'Does the reference list above contain an entry for the paper titled "{target}"? '
                "Answer true only if one of the listed entries is that paper.",
            )
            out.append((paper, _item(q, state, kind == "true", "citation", kind, paper, seed)))
            made += 1
    return out


# ── shared ────────────────────────────────────────────────────────────────────


def _item(q: Question, state: str, label: bool | int | str, task: str, kind: str, source: str, seed: int):
    # id and split are assigned by the caller once all items exist
    return BenchmarkItem(
        id="pending",
        task=task,
        split="dev",
        question=q,
        state=state,
        label=label,
        construction={"kind": kind, "source": source, "seed": seed},
        generator=GENERATOR,
    )

"""Numeric-consistency check (AUD-F-04) of the write-up against the run's own results.

The reference is `results.json`: the harness's numbers for every method, dataset and metric. Numbers are extracted
from the write-up *as written*, not from any markup the writer was given:

- **Table cells** (`mean ± std`) are compared with the rendered values in `results.json`; any difference is a `fail`.
- **Prose numbers**: a number with a decimal point, a percent sign, or more than ten, outside the reference list,
  citation brackets, years and arXiv ids. It must be a value in `results.json` as rounded to the precision written
  (a mean or std of any method, dataset or metric), or a difference, percent change or ratio between two of them
  (a "40% lower" is derived), or a configuration number the report may state (seeds, ideas, trees, the paper's
  reference values and tolerance). A number that is none of these is a `fail` in a results claim (a sentence about
  results: residual, MSE, runtime, baseline, better, lower, %, ...) and a `warn` elsewhere.
- **Results claims that state a table value** (a mean or std, not only a derived figure or a configuration number)
  and whose numbers all exist go to the judge with the benchmark's `num.claim_consistent` question and the full
  results table (held-out and in-sample residuals, runtime): a real number attached to the wrong method or dataset is
  a different fault from an invented one. The benchmark measured the judge on crisp cell claims, not loose prose, so
  its "no" on a whole sentence is a `warn` (unconfirmed), not a `fail`; only the deterministic checks fail a paper.
  Known limit: a misattributed real number is flagged amber, not red.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.loop import tables
from vera.schemas import Claim, Evidence, Finding, Location, Question, QuestionType, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]

NUMERIC_NOTE = " Ignore any ± term and formatting marks such as bold or asterisks; the value must match as written."
AUDIT_METRICS: tuple[tuple[str, str], ...] = (
    ("residual_mse_pct", "Residual MSE, held-out (%)"),
    ("residual_in_sample_pct", "Residual MSE, in-sample (%)"),
    ("runtime_s", "Runtime (s)"),
)
TABLE_NAMES = {
    "Residual MSE (%)": "residual_mse_pct",
    "Residual MSE, held-out (%)": "residual_mse_pct",
    "Residual MSE, in-sample (%)": "residual_in_sample_pct",
    "Runtime (s)": "runtime_s",
}
RESULT_WORDS = re.compile(
    r"residual|mse|mae|rmse|error|cvar|stability|spearman|runtime|seconds|baseline|beat|better|worse|lower|higher|"
    r"improv|reduc|increase|slower|faster",
    re.IGNORECASE,
)  # a bare "%" or "±" does not make a sentence a results claim: "top-k covering 95% of the gain" is a method choice
COMPARISON = re.compile(
    r"\b(better|worse|lower|higher|faster|slower|improv\w+|degrad\w+|beat\w*|outperform\w*|reduc\w+|increas\w+|rose|fell)\b",
    re.IGNORECASE,
)  # a direction word: a sentence with one and no number is still a claim about the table
# A claim about every column or dataset needs the whole table read at once: the cheap judge was confidently wrong on one
# in a clean write-up (Increment 3 dev run), so universal comparisons are not put to it.
UNIVERSAL = re.compile(r"\b(every|all|both|each|neither|any|no idea|none)\b", re.IGNORECASE)
LEGEND = re.compile("[↓↑]|(lower|higher) is better", re.IGNORECASE)  # the table's own legend is not a claim
METHOD_SECTIONS = ("method", "approach")  # numbers here are design choices (thresholds, depths): unverifiable, a warn
NUMBER = re.compile(r"(?<![\w.\[\-])(\d+(?:\.\d+)?)(\s*%)?")
STRIP = [
    re.compile(r"\[R\d+\]"),
    re.compile(r"arXiv:\s*\d+\.\d+(v\d+)?", re.I),
    re.compile(r"https?://\S+"),
    re.compile(r"\bC\d+\b"),
    re.compile(r"\b(Table|Figure|Fig\.|Section|Eq\.)\s*\d+", re.I),
]


def decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def matches(x: str, known: set[float]) -> bool:
    """x equals some known value rounded to the precision x is written in."""
    half = 0.5 * 10 ** -decimals(x) + 1e-9
    v = float(x)
    return any(abs(k - v) <= half for k in known)


def metric_defs(results_json: dict) -> tuple[tuple[str, str], ...]:
    """(key, column name) of the metrics the run reports: its own list when results.json has one, else TreeHFD's."""
    return tuple((k, n) for k, n in results_json["metrics"]) if results_json.get("metrics") else AUDIT_METRICS


def metrics_of(results_json: dict) -> tuple[tuple[str, str], ...]:
    """The audit metrics every method has on every dataset (results from before the in-sample residual lack it)."""
    results, datasets = results_json["results"], results_json["datasets"]
    return tuple(
        (k, n) for k, n in metric_defs(results_json) if all(k in res[d] for res in results.values() for d in datasets)
    )


def known_values(results_json: dict, target: dict | None = None) -> set[float]:
    """Every value the report may state: results.json's values (see `result_values`) and the config numbers."""
    return {round(k, 6) for k in result_values(results_json) | config_values(results_json, target)}


def result_values(results_json: dict) -> set[float]:
    """The values the results table (and results.json) carries: means and stds, differences, percent changes, ratios.

    Only a sentence with one of these is a claim about the table, so only those go to the judge: a sentence whose
    only numbers are configuration values ("100 trees") or the paper's reference value is not about the table."""
    known: set[float] = set()
    results, datasets = results_json["results"], results_json["datasets"]
    base = results.get(tables.BASELINE, {})
    for method, res in results.items():
        for d in datasets:
            for key, _ in metrics_of(results_json):
                cell = res[d][key]
                known |= {cell["mean"], cell["std"]}
                if method != tables.BASELINE and d in base:
                    b = base[d][key]["mean"]
                    diff = b - cell["mean"]
                    known |= {diff, abs(diff)}
                    if b:
                        known |= {abs(diff) / abs(b) * 100, cell["mean"] / b, cell["mean"] / b * 100}
    for d in datasets:  # the baseline's own values for every metric it has: the paper states them (the basis)
        for cell in base.get(d, {}).values():
            if isinstance(cell, dict) and "mean" in cell:
                known |= {cell["mean"], cell["std"]}
    return {round(k, 6) for k in known | protocol_values(results_json)}


def protocol_values(results_json: dict) -> set[float]:
    """The means and stds of every cell of the registered protocol, when the run has one (Increment 4)."""
    out: set[float] = set()
    for cells in (results_json.get("protocol") or {}).get("results", {}).values():
        for cell in cells.values():
            if cell.get("valid"):
                for v in cell.values():
                    if isinstance(v, dict) and "mean" in v:
                        out |= {v["mean"], v["std"]}
    return {round(v, 6) for v in out}


def direct_values(results_json: dict) -> set[float]:
    """Just the means and stds as the table shows them: what a sentence must contain to be put to the judge."""
    out: set[float] = set()
    for res in results_json["results"].values():
        for d in results_json["datasets"]:
            for key, _ in metrics_of(results_json):
                out |= {res[d][key]["mean"], res[d][key]["std"]}
    return {round(v, 6) for v in out | protocol_values(results_json)}


def config_values(results_json: dict, target: dict | None = None) -> set[float]:
    """Numbers a report may state that are not in the table: seeds, ideas, methods, datasets, trees, and the paper's
    reference values and tolerance."""
    known = {
        float(results_json["n_seeds"]),
        float(len(results_json["ideas"])),
        float(len(results_json["results"]) - 1),
        float(len(results_json["datasets"])),
        100.0,
    }
    protocol = results_json.get("protocol")
    if protocol:  # the registered design: the correlations, seeds and refits are configuration, not results
        known |= {float(d.split("@")[1]) for d in protocol["datasets"] if "@" in d}
        known |= {float(protocol["n_seeds"]), float(protocol["n_boot"]), float(len(protocol["methods"]))}
    if target and "absolute_pct_points" in target.get("tolerance", {}):
        known.add(float(target["tolerance"]["absolute_pct_points"]))
        known |= {float(v["reference_pct"]) for v in target["datasets"].values() if "reference_pct" in v}
    elif target and "relative" in target.get("tolerance", {}):  # the second problem's registered target
        known.add(float(target["tolerance"]["relative"]) * 100)
        refs = [ref for ref in target["reference"].values() if isinstance(ref, dict)]
        known |= {float(m[0]) for ref in refs for m in ref.values() if isinstance(m, list)}
    return {round(k, 6) for k in known}


# ── extraction ───────────────────────────────────────────────────────────────────────────────────────


def sentences(text: str) -> list[tuple[str, str]]:
    """(section heading, sentence) for the prose of the write-up: no tables, no reference list, no headings."""
    body = text.partition("## References")[0]
    out, section = [], ""
    for block in body.split("\n"):
        line = block.strip()
        if not line or line.startswith("|"):
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        line = re.sub(r"^[-*]\s+|^\d+[.)]\s+", "", line)
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[\(\"*])", line):
            if s.strip():
                out.append((section, s.strip()))
    return out


def numbers_in(sentence: str) -> list[str]:
    """The number strings in a sentence that must be backed by results.json."""
    s = sentence
    for pat in STRIP:
        s = pat.sub(" ", s)
    found = []
    for m in NUMBER.finditer(s):
        x, pct = m.group(1), bool(m.group(2))
        if "." not in x and not pct:
            if 1900 <= int(x) <= 2100 or int(x) <= 10:
                continue  # a year, or a small count ("3 seeds", "two ideas")
        found.append(x)
    return found


# ── checks ───────────────────────────────────────────────────────────────────────────────────────────


def dataset_key(label: str, results_json: dict) -> str:
    """The results.json dataset a table column label names. The label is the dataset name with underscores shown as
    spaces and a capital, so the name is read back by comparing letters and digits only (`analytical_rho0` is labelled
    "Analytical rho0"); an unknown label is returned lower-cased, as before, and its cells then fail as unmatched."""
    flat = re.sub(r"[^a-z0-9]", "", label.lower())
    names = set(results_json.get("datasets") or [])
    for res in results_json["results"].values():
        names |= set(res)
    return next((n for n in sorted(names) if re.sub(r"[^a-z0-9]", "", n.lower()) == flat), label.strip().lower())


def table_blocks(text: str) -> list[tuple[str, list[str]]]:
    """(the non-empty line before it, its rows) for each markdown table in the body before the reference list."""
    lines = text.partition("## References")[0].splitlines()
    blocks, i = [], 0
    while i < len(lines):
        if not lines[i].startswith("|"):
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j].startswith("|"):
            j += 1
        before = next((ln.strip() for ln in reversed(lines[:i]) if ln.strip()), "")
        blocks.append((before, lines[i:j]))
        i = j
    return blocks


def protocol_table_findings(text: str, results_json: dict) -> tuple[list[Claim], list[Finding]]:
    """Every cell of the registered protocol's tables against `results_json["protocol"]`: a bold title names the metric,
    each column a dataset, each row a method; `invalid` and `n/a` must be what the results say."""
    claims: list[Claim] = []
    findings: list[Finding] = []
    protocol = results_json.get("protocol")
    if not protocol:
        return claims, findings
    by_title = {title: key for key, title, _ in tables.PROTOCOL_METRICS}
    by_label = {tables.protocol_dataset_label(d): d for d in protocol["datasets"]}
    for before, rows in table_blocks(text):
        title = re.match(r"\*\*(.+?)\*\*", before)
        metric = by_title.get(title.group(1)) if title else None
        if metric is None or len(rows) < 3:
            continue
        header = [c.strip() for c in rows[0].strip("|").split("|")]
        cols = [by_label.get(re.sub(r"\s*[↓↑]$", "", h)) for h in header[1:]]
        for ln in rows[2:]:
            cells = [c.strip() for c in ln.strip("|").split("|")]
            method = cells[0]
            for dataset, cell in zip(cols, cells[1:], strict=False):
                where = Location(section="Results", table=f"{dataset} · {metric}", quote=ln[:200])
                claim = Claim(id=f"num:ptable:{method}:{dataset}:{metric}", kind="numeric",
                              text=f"{method}: {cell}", location=where)  # fmt: skip
                claims.append(claim)
                truth = (protocol["results"].get(method) or {}).get(dataset)
                ref = f"results.json:protocol/{method}/{dataset}/{metric}"
                if truth is None:
                    why = f"The protocol table row {method!r} / {dataset} has no counterpart in results.json."
                    findings.append(_f("numeric", "fail", claim, "log", ref, False, why))
                    continue
                want = tables.protocol_cell_text(truth, metric)
                if cell != want:
                    findings.append(_f("numeric", "fail", claim, "log", ref, False,
                                       f"The protocol table says {cell!r} for {method} on {dataset} ({metric}); "
                                       f"results.json has {want!r}."))  # fmt: skip
    return claims, findings


def table_findings(text: str, results_json: dict) -> tuple[list[Claim], list[Finding]]:
    claims, findings = [], []
    results = results_json["results"]
    main = [rows for _, rows in table_blocks(text) if " · " in rows[0]]  # the results table: "Dataset · Metric" columns
    rows = main[0] if main else []
    if len(rows) < 3:
        return claims, findings
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    names = {**TABLE_NAMES, **{label: key for key, label in metric_defs(results_json)}}
    cols = []
    for h in header[1:]:
        m = re.match(r"(.+?) · (.+?) ↓$", h)
        cols.append((dataset_key(m.group(1), results_json), names.get(m.group(2).strip())) if m else (None, None))
    for ln in rows[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        method = cells[0]
        for (dataset, metric), cell in zip(cols, cells[1:], strict=False):
            claim = Claim(
                id=f"num:table:{method}:{dataset}:{metric}",
                kind="numeric",
                text=f"{method}: {cell}",
                location=Location(section="Results", table=f"{dataset} · {metric}", quote=ln[:200]),
            )
            claims.append(claim)
            ref = f"results.json:{method}/{dataset}/{metric}"
            truth = None if method not in results else results[method].get(dataset, {}).get(metric)
            m = re.match(r"([\d.]+) ± ([\d.]+)", cell)
            if truth is None or not m:
                findings.append(
                    _f(
                        "numeric",
                        "fail",
                        claim,
                        "log",
                        ref,
                        False,
                        f"The table row {method!r} / {dataset} / {metric} has no counterpart in results.json "
                        f"or is not 'mean ± std': {cell!r}.",
                    )
                )
                continue
            want = (tables.fmt_sig(truth["mean"]), tables.fmt_sig(truth["std"], 2))
            if (float(m.group(1)), float(m.group(2))) != (float(want[0]), float(want[1])):
                findings.append(
                    _f(
                        "numeric",
                        "fail",
                        claim,
                        "log",
                        ref,
                        False,
                        f"The table says {cell!r} for {method} on {dataset} ({metric}); results.json "
                        f"has {want[0]} ± {want[1]}.",
                    )
                )
    return claims, findings


def _f(check, severity, claim, source, reference, matched, summary, verdicts=()) -> Finding:
    return Finding(
        check=check,
        severity=severity,
        claim_ids=[claim.id],
        verdicts=list(verdicts),
        summary=summary,
        evidence=[Evidence(claim_id=claim.id, source=source, reference=reference, matched=matched, detail=summary)],
    )


def audit_numbers(
    text: str, results_json: dict, ask: Ask, target: dict | None = None
) -> tuple[list[Claim], list[Finding]]:
    claims, findings = table_findings(text, results_json)
    more_claims, more_findings = protocol_table_findings(text, results_json)
    claims, findings = claims + more_claims, findings + more_findings
    known = known_values(results_json, target)
    from_table = direct_values(results_json)
    results, datasets = results_json["results"], results_json["datasets"]
    material = tables.render_results(results, datasets, results_json["n_seeds"], metrics_of(results_json))
    proto = protocol_values(results_json)
    if results_json.get("protocol"):  # the judge reads the protocol's tables too
        material += "\n\n" + tables.render_protocol(results_json["protocol"])
    context: list[str] = []  # the ideas the text has been discussing, for sentences that name none ("Its MSE was ...")
    last_section = None
    for n, (section, sentence) in enumerate(sentences(text)):
        from vera.audit import alignment  # noqa: PLC0415

        if section != last_section:
            context, last_section = [], section
        named_ideas = alignment.idea_methods(sentence, results)
        mine, context = list(context), (named_ideas or context)  # this sentence sees the context before it
        nums = numbers_in(sentence)
        if not nums:
            # A comparison with no number ("C3 was worse than the baseline on every column") is still a claim about the
            # table, and flipping its direction word leaves every number right: the judge reads it against the table.
            about_table = alignment.named_methods(sentence, results) or mine
            in_method = section.lower().startswith(METHOD_SECTIONS)
            judgeable = not LEGEND.search(sentence) and not UNIVERSAL.search(sentence)
            if COMPARISON.search(sentence) and judgeable and about_table and not in_method:
                claim = Claim(id=f"num:{n}", kind="numeric", text=sentence,
                              location=Location(section=section or None, quote=sentence[:200]))  # fmt: skip
                claims.append(claim)
                question = Question(
                    id="num.claim_consistent",
                    type=QuestionType.BOOLEAN,
                    text=f"Is this claim consistent with the table? Claim: {sentence}" + NUMERIC_NOTE,
                )
                verdict, confident = ask(question, material)
                if not confident or verdict.answer is not True:
                    findings.append(
                        _f("numeric", "warn", claim, "log", "results.json (rendered table)",
                           None if not confident else False,
                           f"Could not confirm the comparison against the table: {sentence[:160]!r}", [verdict])
                    )  # fmt: skip
            continue
        is_result = bool(RESULT_WORDS.search(sentence)) and not section.lower().startswith(METHOD_SECTIONS)
        claim = Claim(
            id=f"num:{n}",
            kind="numeric",
            text=sentence,
            value=float(nums[0]),
            location=Location(section=section or None, quote=sentence[:200]),
        )
        claims.append(claim)
        unknown = [x for x in nums if not matches(x, known)]
        if unknown:
            findings.append(
                _f(
                    "numeric",
                    "fail" if is_result else "warn",
                    claim,
                    "log",
                    "results.json",
                    False,
                    f"{', '.join(unknown)} in {'a results claim' if is_result else 'the text'} "
                    f"is not a value in results.json (nor a difference or ratio of two): {sentence[:160]!r}",
                )
            )
            continue
        if not is_result or not any(matches(x, from_table) for x in nums):
            continue  # not a results claim, or none of its numbers comes from the table: nothing for the judge to check
        # a protocol value sits in many cells of its own tables: only the results table's numbers are placed by name
        placed = [x for x in nums if not matches(x, proto)]
        misplaced = alignment.misplaced(sentence, placed, results_json, from_table, mine)
        if misplaced:
            where = "; ".join(f"{x} is a value of {', '.join(w)}" for x, w in misplaced)
            findings.append(
                _f(
                    "numeric",
                    "fail",
                    claim,
                    "log",
                    "results.json",
                    False,
                    f"A real number on the wrong method or dataset: {where}, not of the cell this sentence names: "
                    f"{sentence[:160]!r}",
                )
            )
            continue
        question = Question(
            id="num.claim_consistent",
            type=QuestionType.BOOLEAN,
            text=f"Is this claim consistent with the table? Claim: {sentence}" + NUMERIC_NOTE,
        )
        verdict, confident = ask(question, material)
        if not confident:
            findings.append(
                _f(
                    "numeric",
                    "warn",
                    claim,
                    "log",
                    "results.json (rendered table)",
                    None,
                    f"Could not confirm against the table (the judge was not confident): {sentence[:160]!r}",
                    [verdict],
                )
            )
        elif verdict.answer is not True:
            findings.append(
                _f(
                    "numeric",
                    "warn",
                    claim,
                    "log",
                    "results.json (rendered table)",
                    False,
                    f"Every number exists in results.json, but the judge could not confirm the claim: "
                    f"{sentence[:160]!r}",
                    [verdict],
                )
            )
    return claims, findings

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
    r"residual|mse|runtime|seconds|baseline|beat|better|worse|lower|higher|improv|reduc|increase|slower|faster",
    re.IGNORECASE,
)  # a bare "%" or "±" does not make a sentence a results claim: "top-k covering 95% of the gain" is a method choice
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


def metrics_of(results_json: dict) -> tuple[tuple[str, str], ...]:
    """The audit metrics every method has on every dataset (results from before the in-sample residual lack it)."""
    results, datasets = results_json["results"], results_json["datasets"]
    return tuple((k, n) for k, n in AUDIT_METRICS if all(k in res[d] for res in results.values() for d in datasets))


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
    return {round(k, 6) for k in known}


def direct_values(results_json: dict) -> set[float]:
    """Just the means and stds as the table shows them: what a sentence must contain to be put to the judge."""
    out: set[float] = set()
    for res in results_json["results"].values():
        for d in results_json["datasets"]:
            for key, _ in metrics_of(results_json):
                out |= {res[d][key]["mean"], res[d][key]["std"]}
    return {round(v, 6) for v in out}


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
    if target:
        known.add(float(target["tolerance"]["absolute_pct_points"]))
        known |= {float(v["reference_pct"]) for v in target["datasets"].values()}
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


def table_findings(text: str, results_json: dict) -> tuple[list[Claim], list[Finding]]:
    claims, findings = [], []
    results = results_json["results"]
    rows = [ln for ln in text.partition("## References")[0].splitlines() if ln.startswith("|")]
    if len(rows) < 3:
        return claims, findings
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    cols = []
    for h in header[1:]:
        m = re.match(r"(.+?) · (.+?) ↓$", h)
        cols.append((m.group(1).strip().lower(), TABLE_NAMES.get(m.group(2).strip())) if m else (None, None))
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
    known = known_values(results_json, target)
    from_table = direct_values(results_json)
    results, datasets = results_json["results"], results_json["datasets"]
    material = tables.render_results(results, datasets, results_json["n_seeds"], metrics_of(results_json))
    for n, (section, sentence) in enumerate(sentences(text)):
        nums = numbers_in(sentence)
        if not nums:
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

"""Claim-cell alignment: a real number attached to the wrong method or dataset is a `fail`, not a `warn`.

The Increment 2 numeric rule failed a number that exists nowhere in `results.json` but could only warn about a number
that exists and sits on the wrong method or dataset (the judge's "no" on a loose sentence is unconfirmed, not proof).
That is the amber class the Increment 2 review named. This rule is deterministic: in a results sentence that names
methods and/or datasets, every number that is a table value must be a value of a named method on a named dataset
(or of the baseline, which a sentence compares against by default, or a difference or ratio of such cells).

It deliberately says nothing when the sentence names no method or no dataset (nothing to align with), when a number is
not a table value (the unknown-number rule handles it) and when the sentence names a metric, not a cell, as the thing
it describes: the rule checks WHERE a number lives, never whether the sentence's wording about it is fair.
"""

from __future__ import annotations

import re

from vera.audit.numbers import matches, metrics_of
from vera.loop import tables

ALL_WORDS = re.compile(r"\b(both|each|every|all|either|neither|across)\b[^.]{0,30}\bdatasets?\b", re.IGNORECASE)


def aliases(method: str) -> list[str]:
    """Ways a write-up names a method: its full label, its code ("C2"), its name after the code, and for the baseline
    "baseline" and "TreeHFD" (the method it is)."""
    out = [method]
    if ":" in method:
        code, name = (p.strip() for p in method.split(":", 1))
        out += [code, name]
    if method == tables.BASELINE:
        out += ["baseline", tables.PROBLEM_NAME]
    return [a for a in out if a]


def named(sentence: str, words: list[str]) -> bool:
    return any(re.search(rf"(?<![\w]){re.escape(w)}(?![\w])", sentence, re.IGNORECASE) for w in words)


def named_methods(sentence: str, results: dict) -> list[str]:
    return [m for m in results if named(sentence, aliases(m))]


def named_datasets(sentence: str, datasets: list[str]) -> list[str]:
    if ALL_WORDS.search(sentence):
        return list(datasets)
    return [d for d in datasets if named(sentence, [d, tables.dataset_label(d)])]


IN_SAMPLE = re.compile(r"in[- ]sample|training", re.IGNORECASE)
HELD_OUT = re.compile(r"held[- ]out|test set|out[- ]of[- ]sample", re.IGNORECASE)


def metric_keys(sentence: str, available: set[str] | None = None) -> set[str]:
    """The metrics a sentence may be quoting. The write-ups report a held-out residual (the default), an in-sample
    residual (when the sentence says in-sample or training) and the runtime, and the one thing wording settles is
    which residual: a sentence that says "in-sample" quotes the in-sample column, any other sentence the held-out one.
    Runtime is always allowed (a sentence on residuals and runtime may quote both)."""
    if available is not None and "residual_mse_pct" not in available:
        return set(available)  # another problem's metrics: the wording does not tell them apart, all are allowed
    keys = {"runtime_s"}
    in_sample, held_out = bool(IN_SAMPLE.search(sentence)), bool(HELD_OUT.search(sentence))
    if in_sample:
        keys.add("residual_in_sample_pct")
    if held_out or not in_sample:
        keys.add("residual_mse_pct")
    return keys


def cell_values(results_json: dict, methods: list[str], datasets: list[str],
                metrics: set[str] | None = None) -> set[float]:  # fmt: skip
    """Means, stds, and the differences, percent changes and ratios against the baseline of the given cells (of the
    given metrics, when the sentence's wording names them)."""
    results = results_json["results"]
    base = results.get(tables.BASELINE, {})
    out: set[float] = set()
    for method in methods:
        for d in datasets:
            for key, _ in metrics_of(results_json):
                if metrics and key not in metrics:
                    continue
                cell = results[method][d][key]
                out |= {cell["mean"], cell["std"]}
                if method != tables.BASELINE and d in base:
                    b = base[d][key]["mean"]
                    diff = b - cell["mean"]
                    out |= {diff, abs(diff)}
                    if b:
                        out |= {abs(diff) / abs(b) * 100, cell["mean"] / b, cell["mean"] / b * 100}
    return {round(v, 6) for v in out}


def significant_digits(x: str) -> int:
    digits = x.replace(".", "").lstrip("0")
    return len(digits)


def idea_methods(sentence: str, results: dict) -> list[str]:
    """The non-baseline methods a sentence names."""
    return [m for m in named_methods(sentence, results) if m != tables.BASELINE]


def misplaced(
    sentence: str, numbers: list[str], results_json: dict, direct: set[float], context: list[str] | None = None
) -> list[tuple[str, list[str]]]:
    """Numbers in `sentence` that are table values but not values of the cells it names: [(number, where it lives)].

    `direct` is every mean and std in the table (`vera.audit.numbers.direct_values`). `context` is the idea the text
    has been discussing: a sentence that names no idea of its own ("Its held-out MSE was 17.7 on Analytical, versus
    2.79 for TreeHFD") is about that one, so its cells are allowed too. Only numbers written with at least three
    significant digits are checked: "2.5" collides with some cell by chance often enough to be a false alarm."""
    results, datasets = results_json["results"], results_json["datasets"]
    methods = named_methods(sentence, results)
    ds = named_datasets(sentence, datasets)
    if not methods or not ds:
        return []
    allowed_methods = {*methods, tables.BASELINE}
    if not idea_methods(sentence, results):
        allowed_methods |= set(context or [])  # no idea named: the sentence is about the one under discussion
    available = {k for k, _ in metrics_of(results_json)}
    allowed = cell_values(results_json, sorted(allowed_methods & set(results)), ds, metric_keys(sentence, available))
    bad = []
    for x in numbers:
        if significant_digits(x) < 3 or matches(x, allowed) or not matches(x, direct):
            continue
        where = [f"{m} / {d}" for m, res in results.items() for d in datasets for key, _ in metrics_of(results_json)
                 if matches(x, {round(res[d][key]["mean"], 6), round(res[d][key]["std"], 6)})]  # fmt: skip
        bad.append((x, sorted(set(where))[:3]))
    return bad

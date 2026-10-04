# ruff: noqa: E501
"""The ablation stage (RSH-F-04, Increment 4): when an idea wins somewhere, find out which part of it did the work.

After the idea gate and the protocol, if an idea beats the baseline on the primary metric on at least one registered dataset
(the best such idea), the generator is shown its description and code and asked for variants that remove or disable each
described component, one at a time. Each variant runs through the same harness on the same seeds. The variants join the
loop's results under the label `<idea> without <component>`, so the write-up's results table, the figures and the audit treat
them like any method: the harness's numbers, in the same table, checked cell by cell. When no idea beats the baseline
anywhere nothing is run, and `artifacts/ablation.json` and the paper say so with the reason.

The variants are written by the model (like the ideas); a variant the harness rejects is recorded with its error and is not
retried: an ablation that cannot be built is reported as such, never filled in.
"""

from __future__ import annotations

from collections.abc import Callable

from vera.loop import problem, tables
from vera.loop.protocol_stage import idea_sources
from vera.loop.stages import LoopDeps, _extract_json, _write_json, extract_code, run_harness

MAX_COMPONENTS = 3
ABLATION_SYSTEM = (
    "You are a careful scientific programmer. Reply with the JSON asked for and nothing else of substance."
)


def winner(state: dict, deps: LoopDeps) -> tuple[str | None, list[str]]:
    """(the idea that beats the baseline on the most datasets, those datasets), or (None, []) when none beats it anywhere.
    A win is a strictly lower rendered mean of the primary metric, as the gate reads the table."""
    results = state["results"]
    shown = tables.valid_datasets(results, deps.datasets)
    means = tables.rendered_means(results, deps.datasets)
    wins = {m: [d for d in shown if tables.beats(means, m, d)] for m in results if m != tables.BASELINE}
    best = max(wins, key=lambda m: len(wins[m]), default=None)
    return (best, wins[best]) if best and wins[best] else (None, [])


def ablation_prompt(name: str, description: str, code: str) -> str:
    fn = problem.active().function_name
    return (
        f"This idea beat the baseline on at least one dataset.\n\nIdea: {name}\n{description}\n\nIts code:\n```python\n{code}\n```\n\n"
        f"Name up to {MAX_COMPONENTS} components of the idea (separate steps or choices that the description names). For each, write "
        f"the complete module again with only that component removed or disabled (every `{fn}` keeps the same interface). "
        'Reply with a JSON array of objects {"component": "<2-5 words>", "code": "<the complete module>"} and nothing else.'
    )


def ablation_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        name, datasets = winner(state, deps)
        if name is None:
            reason = "no idea beat the baseline on the primary metric on any registered dataset, so no ablation was run"
            return {"artifacts": {"ablation_raw": _write_json(deps, "ablation", {"ran": False, "reason": reason})},
                    "ablation_note": reason}  # fmt: skip
        code = idea_sources(state, deps).get(name)
        by_name = {i["name"]: i for i in state["ideas"]}
        if code is None:
            reason = f"the code of {name} was not kept"
            return {"artifacts": {"ablation_raw": _write_json(deps, "ablation", {"ran": False, "reason": reason})},
                    "ablation_note": reason}  # fmt: skip
        reply = deps.generator.generate(ABLATION_SYSTEM, ablation_prompt(name, by_name[name]["description"], code),
                                        component="p3.ablation")  # fmt: skip
        raw = _extract_json(reply, "[", "]")
        variants = [v for v in (raw if isinstance(raw, list) else []) if isinstance(v, dict) and v.get("component") and v.get("code")]
        results = dict(state["results"])
        log = []
        for k, v in enumerate(variants[:MAX_COMPONENTS], start=1):
            source = extract_code(f"```python\n{v['code']}\n```") or v["code"]
            res, error = run_harness(deps, f"ablation_{k}", source)
            label = f"{name} without {str(v['component']).strip()}"
            ok = error is None and res is not None
            if ok:
                results[label] = res
            log.append({"component": v["component"], "label": label, "ok": ok, "error": error})
        artifact = _write_json(deps, "ablation", {"ran": True, "idea": name, "wins_on": datasets, "variants": log})
        if not any(entry["ok"] for entry in log):
            note = f"an ablation of {name} was attempted and no variant ran: " + "; ".join(
                f"{e['component']}: {e['error']}" for e in log) if log else f"the generator proposed no ablation of {name}"
            return {"artifacts": {"ablation_raw": artifact}, "ablation_note": note, "trail": ["ablation"]}
        return {"results": results, "artifacts": {"ablation_raw": artifact}, "ablation_note": None, "trail": ["ablation"]}

    return node


def facts(state: dict) -> list[str]:
    """The ablation, in words for the write-up prompt (the numbers are in the results table)."""
    if state.get("ablation_note"):
        return [f"- Ablation: {state['ablation_note']}."]
    rows = [m for m in state.get("results", {}) if " without " in m]
    if not rows:
        return []
    return ["- Ablation of the winning idea, run on the same seeds and datasets, one component removed at a time "
            f"(rows of the results table): {'; '.join(rows)}."]  # fmt: skip


__all__ = ["ablation_node", "facts", "winner"]

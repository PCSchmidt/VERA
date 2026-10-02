"""The loop's stages as graph nodes: baseline, ideas, subset experiments (RSH-F-02, RSH-F-03).

Each stage is a *producer* node (generates or runs; model and sandbox calls) followed by a *gate* node (the judge's
verdict, from a component other than the producer). They are separate nodes so a crash during a gate never repeats
the producer's billed calls on resume. Every gate verdict is also appended, with its material and the programmatic
shadow answer where one exists, to `gates.jsonl` in the run directory: the real gate decisions the Increment 2
judge re-test is built from.

Dependencies are injected (`LoopDeps`), so the whole graph runs offline with fake generators, judges and sandboxes.
Agent-written code only ever runs through `deps.sandbox`; the metric is computed by VERA's harness inside it.
"""

from __future__ import annotations

import json
import operator
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Protocol, TypedDict

from vera.graph import Judge
from vera.ledger import Ledger
from vera.loop import questions, tables
from vera.sandbox import SandboxLimits, SandboxResult
from vera.schemas import STAGES, Budget, Question, RunSpec, SelfGradingError, StageResult, Verdict

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "docker" / "sandbox-treehfd" / "harness.py"
PRODUCERS = {
    "baseline": "p3.baseline",
    "ideate": "p3.ideate",
    "subset_exp": "p3.subset_exp",
    "write_up": "p3.write_up",
    "audit": "p1.audit",
}
MAX_ATTEMPTS = 2  # an experiment script gets one retry with the error message
MIN_IDEA_SCORE = 3
EXPERIMENT_LIMITS = SandboxLimits(wall_seconds=900, memory_mb=2048, cpus=2.0, pids=256)


class Generator(Protocol):
    def generate(self, system: str, prompt: str, *, component: str) -> str: ...


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


class LoopState(TypedDict, total=False):
    baseline: dict  # the harness's per-dataset results for the baseline
    ideas: list[dict]  # [{"name", "description"}]
    selected: list[str]  # idea names chosen for a subset run
    results: dict  # method name -> per-dataset results (baseline first), valid runs only
    best: str | None  # the best idea that beats the baseline everywhere, if any
    artifacts: Annotated[dict, _merge]  # stage -> artifact path
    verdicts: Annotated[dict, _merge]  # question key -> Verdict JSON
    stage_results: Annotated[list, operator.add]  # StageResult JSON, in order
    trail: Annotated[list, operator.add]
    stop: dict | None  # {"stage", "reason"} once the run has stopped
    budget: dict  # the Budget after the last completed node, so a resumed process restores what was spent


@dataclass
class LoopDeps:
    spec: RunSpec
    target: dict  # docs/results/treehfd_baseline_target.json
    generator: Generator
    judge: Judge
    sandbox: Callable[..., SandboxResult]
    budget: Budget
    run_dir: Path
    data_dir: Path  # host directory holding the datasets (copied into each sandbox working directory)
    ledger: Ledger | None = None  # the run's ledger; on resume, spend is restored from it as well as the snapshot
    min_confidence: float = 0.7
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def datasets(self) -> list[str]:
        return list(self.spec.problem.datasets)

    @property
    def n_seeds(self) -> int:
        return int(self.spec.problem.subset.get("n_seeds", 3))


# ── helpers ──────────────────────────────────────────────────────────────────────────────────────────


def _write_json(deps: LoopDeps, name: str, data: Any) -> str:
    path = deps.run_dir / "artifacts" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return path.relative_to(deps.run_dir).as_posix()


def _stop(stage: str, reason: str) -> dict:
    return {"stop": {"stage": stage, "reason": reason}}


def finish(update: dict) -> dict:
    """A stage that stopped the run is not completed: drop its entry from `artifacts` (the raw artifact stays)."""
    if update.get("stop") and "artifacts" in update:
        update["artifacts"] = {k: v for k, v in update["artifacts"].items() if k not in STAGES}
    return update


def _prepare_workdir(deps: LoopDeps, name: str) -> Path:
    wd = deps.run_dir / "work" / name
    if wd.exists():
        shutil.rmtree(wd)
    (wd / "data").mkdir(parents=True)
    shutil.copy(HARNESS, wd / "harness.py")
    for f in deps.data_dir.glob("*"):
        if f.is_file():
            shutil.copy(f, wd / "data" / f.name)
    return wd


def run_harness(deps: LoopDeps, name: str, method_source: str | None) -> tuple[dict | None, str | None]:
    """Run the harness on `deps.datasets` in a fresh sandbox working directory.

    `method_source` is the idea's `decompose` module (None runs the parent's baseline). Returns (results, error):
    results is the harness's per-dataset dict when it ran, error says why not (or what the method's error was).
    """
    wd = _prepare_workdir(deps, name)
    if method_source is not None:
        (wd / "method.py").write_text(method_source, encoding="utf-8")
    method = "/work/method.py" if method_source is not None else "baseline"
    driver = (
        "import sys\nsys.path.insert(0, '/work')\nimport harness\n"
        f"harness.main(['--method', {method!r}, '--datasets', {','.join(deps.datasets)!r}, "
        f"'--seeds', '{deps.n_seeds}'])\n"
    )
    res = deps.sandbox(driver, wd, limits=EXPERIMENT_LIMITS, budget=deps.budget)
    if res.timed_out or res.oom_killed or res.workdir_over_limit:
        why = "timed out" if res.timed_out else "ran out of memory" if res.oom_killed else "wrote too much"
        return None, f"the experiment {why}"
    result_file = wd / "result.json"
    if res.exit_code != 0 or not result_file.exists():
        return None, f"the harness failed (exit {res.exit_code}): {res.stderr[-600:]}"
    out = json.loads(result_file.read_text(encoding="utf-8"))
    if out.get("error"):
        return None, f"the method raised: {out['error'][-600:]}"
    invalid = {d: r["invalid_reason"] for d, r in out["datasets"].items() if not r.get("valid")}
    if invalid:
        return out["datasets"], "invalid decomposition: " + "; ".join(f"{d}: {m}" for d, m in invalid.items())
    return out["datasets"], None


def ask_gate(
    deps: LoopDeps, stage: str, question: Question, material: str, shadow: Any, state: dict, producer: str | None = None
) -> tuple[Verdict, bool]:
    """Ask the judge one question about `material`. Returns (verdict, confident).

    The verdict is stamped with the stage's producer id; a judge that *is* the producer raises SelfGradingError.
    It is appended to gates.jsonl with the shadow answer. `confident` is False for a malformed answer or one
    below `min_confidence`: an unclear gate never counts as a pass (fail closed). `producer` names the producer of
    the material when it is not the stage's own (the audit judges the write-up's text, produced by p3.write_up).
    """
    producer = producer or PRODUCERS[stage]
    (verdict,) = deps.judge.ask(material, [question])
    if verdict.judge_id == producer:
        raise SelfGradingError(f"{question.id}: judge {verdict.judge_id!r} produced the material it judges")
    verdict = verdict.model_copy(update={"producer_id": producer})
    record = {
        "run_id": deps.spec.run_id, "stage": stage, "question": question.model_dump(mode="json"),
        "material": material, "verdict": verdict.model_dump(mode="json"), "shadow_answer": shadow,
        "generator": deps.spec.models.get(stage),
    }  # fmt: skip
    log = deps.run_dir / "gates.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    confident = verdict.confidence_source != "none" and verdict.confidence >= deps.min_confidence
    return verdict, confident


def stage_result(deps: LoopDeps, stage: str, artifact: str, gate: Verdict, decision: str, metrics: dict) -> dict:
    return StageResult(
        run_id=deps.spec.run_id, stage=stage, artifact_ref=artifact, producer_id=PRODUCERS[stage], gate=gate,
        decision=decision, metrics=metrics, budget_after=deps.budget.model_copy(),
    ).model_dump(mode="json")  # fmt: skip


def _extract_json(text: str, opener: str, closer: str) -> Any | None:
    for m in re.finditer(r"```(?:json)?\s*(.*?)```", text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
    start, end = text.find(opener), text.rfind(closer)
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    blocks = [b for b in blocks if "def decompose" in b]
    return blocks[-1].strip() + "\n" if blocks else None


def baseline_example() -> str:
    """The baseline method's source from the harness, shown to the generator as the interface example."""
    text = HARNESS.read_text(encoding="utf-8")
    return text[text.index("def baseline(") : text.index("def load_method(")].strip()


# ── baseline ─────────────────────────────────────────────────────────────────────────────────────────


def baseline_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        results, error = run_harness(deps, "baseline", None)
        artifact = _write_json(deps, "baseline", {"results": results, "error": error})
        if results is None or error:
            return {"artifacts": {"baseline_raw": artifact}, **_stop("baseline", f"baseline run failed: {error}")}
        return {"baseline": results, "artifacts": {"baseline_raw": artifact}, "trail": ["baseline"]}

    return node


def baseline_gate_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        question, material, shadow = questions.baseline_reproduced(
            deps.target, {tables.BASELINE: state["baseline"]}, deps.n_seeds, deps.datasets
        )
        verdict, confident = ask_gate(deps, "baseline", question, material, shadow, state)
        artifact = state["artifacts"]["baseline_raw"]
        passed = confident and verdict.answer is True
        decision = "accept" if passed else "reject"
        sr = stage_result(deps, "baseline", artifact, verdict, decision, {"confidence": verdict.confidence})
        update = {"verdicts": {"baseline": verdict.model_dump(mode="json")}, "stage_results": [sr],
                  "artifacts": {"baseline": artifact}, "trail": ["baseline_gate"]}  # fmt: skip
        if not passed:
            why = "the judge was not confident" if not confident else "the reproduced values are outside tolerance"
            update |= _stop("baseline", f"gate: baseline not reproduced ({why}; shadow answer {shadow})")
        return finish(update)

    return node


# ── ideas ────────────────────────────────────────────────────────────────────────────────────────────

IDEATE_SYSTEM = (
    "You are a machine-learning researcher improving a method for explaining gradient-boosted trees. Reply only "
    "with what is asked, in the requested format."
)


def ideate_prompt(deps: LoopDeps, baseline_table: str, n: int) -> str:
    return (
        "The method is TreeHFD (Benard, NeurIPS 2025), which decomposes an xgboost regression model into an "
        "intercept, main effects (one variable each) and second-order interactions (two variables each), using the "
        "`treehfd` Python package: `XGBTreeHFD(model).fit(X_train, interaction_order=2, interaction_list=None, "
        "depth_variable=None)` then `.predict(X_test)`, which returns main effects (n x p) and interactions (n x q, "
        "columns ordered as `.interaction_list`). Quality is the Residual MSE: the mean squared gap between the "
        "model's predictions and the sum of the components, relative to the variance of the model's predictions, "
        "measured on held-out data (lower is better). The xgboost model is fixed (100 trees, defaults).\n\n"
        f"Baseline results:\n\n{baseline_table}\n\n"
        f"Propose {n} distinct, concrete ideas that could lower the Residual MSE or its runtime, each buildable "
        "in a few minutes on a CPU with numpy, scipy, scikit-learn and the treehfd API (for example: choosing "
        "which interactions to include, the depth at which variables are selected, refitting or recalibrating "
        "components, combining fits). An idea must keep every component a function of only its own variables. "
        'Reply with a JSON array of objects {"name": "<2-5 words>", "description": "<about 50 words: exactly what '
        'is computed>"} and nothing else.'
    )


def ideate_node(deps: LoopDeps) -> Callable[[dict], dict]:
    n_ideas = int(deps.spec.problem.subset.get("n_ideas", 4))

    def node(state: dict) -> dict:
        table = tables.render_results({tables.BASELINE: state["baseline"]}, deps.datasets, deps.n_seeds)
        reply = deps.generator.generate(IDEATE_SYSTEM, ideate_prompt(deps, table, n_ideas), component="p3.ideate")
        raw = _extract_json(reply, "[", "]")
        ideas = []
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and item.get("name") and item.get("description"):
                label = re.sub(r"^C\d+:\s*", "", str(item["name"]).strip())
                ideas.append({"name": f"C{len(ideas) + 1}: {label}", "description": str(item["description"]).strip()})
        ideas = ideas[:n_ideas]
        artifact = _write_json(deps, "ideas", {"ideas": ideas, "raw_reply": reply[-4000:]})
        if not ideas:
            stop = _stop("ideate", "gate: the generator proposed no usable idea")
            return {"artifacts": {"ideate_raw": artifact}, **stop}
        return {"ideas": ideas, "artifacts": {"ideate_raw": artifact}, "trail": ["ideate"]}

    return node


def screen_node(deps: LoopDeps) -> Callable[[dict], dict]:
    """Gate for the ideas stage: score each idea with the judge, keep the best few that clear the bar."""
    n_run = int(deps.spec.problem.subset.get("n_run", 2))

    def node(state: dict) -> dict:
        table = tables.render_results({tables.BASELINE: state["baseline"]}, deps.datasets, deps.n_seeds)
        scored, verdicts = [], {}
        for idea in state["ideas"]:
            question, material = questions.idea_worth_run(idea["name"], idea["description"], table)
            verdict, _ = ask_gate(deps, "ideate", question, material, None, state)
            verdicts[f"idea_worth_run:{idea['name']}"] = verdict.model_dump(mode="json")
            if verdict.confidence_source != "none" and isinstance(verdict.answer, int):  # a ranking, not a pass/fail
                scored.append((verdict.answer, idea["name"], verdict))
        chosen = sorted((s for s in scored if s[0] >= MIN_IDEA_SCORE), key=lambda s: -s[0])[:n_run]  # stable
        artifact = _write_json(deps, "screen", {"scores": {name: score for score, name, _ in scored},
                                                "selected": [name for _, name, _ in chosen]})  # fmt: skip
        gate = (chosen or scored or [(0, "", None)])[0][2]
        update: dict = {"verdicts": verdicts, "artifacts": {"ideate": artifact}, "trail": ["screen"]}
        if gate is None:
            return update | _stop("ideate", "gate: no idea could be scored")
        decision = "accept" if chosen else "reject"
        sr = stage_result(deps, "ideate", artifact, gate, decision, {"n_selected": float(len(chosen))})
        update |= {"selected": [name for _, name, _ in chosen], "stage_results": [sr]}
        if not chosen:
            update |= _stop("ideate", f"gate: no idea scored {MIN_IDEA_SCORE} or more")
        return finish(update)

    return node


# ── subset experiments ───────────────────────────────────────────────────────────────────────────────

IMPLEMENT_SYSTEM = (
    "You are a careful scientific programmer. Reply with one Python code block and nothing else of substance."
)


def implement_prompt(idea: dict, error: str | None, previous: str | None) -> str:
    prompt = (
        "Implement this idea as a Python module defining\n\n"
        "    def decompose(model, X_train, X_test):\n"
        "        ... return eta0, components\n\n"
        "`model` is a fitted xgboost XGBRegressor (100 trees), `X_train` and `X_test` are float numpy arrays. "
        "`eta0` is a float. `components` is a dict mapping a tuple of variable indices to a numpy array with one "
        "value per row of X_test: (j,) for a main effect of variable j, (a, b) with a < b for an interaction. The "
        "harness computes the Residual MSE of `eta0 + sum(components)` against model.predict(X_test) itself. Every "
        "component must depend only on its own variables (the harness checks this by changing the other variables "
        "and rejects the run if the component moves), and `decompose` must work on any number of rows. You may "
        "import numpy, scipy, sklearn, xgboost, treehfd. There is no network. This is the baseline, as the "
        "interface example:\n\n```python\n" + baseline_example() + "\n```\n\n"
        f"Idea: {idea['name']}\n{idea['description']}\n"
    )
    if error:
        prompt += (
            f"\nYour previous attempt failed: {error}\n\nPrevious code:\n```python\n{previous}\n```\nFix it.\n"
        )
    return prompt


def subset_exp_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        by_name = {i["name"]: i for i in state["ideas"]}
        results: dict[str, dict] = {tables.BASELINE: state["baseline"]}
        log: dict[str, Any] = {}
        for name in state["selected"]:
            error, code, attempts = None, None, []
            for attempt in range(1, MAX_ATTEMPTS + 1):
                reply = deps.generator.generate(
                    IMPLEMENT_SYSTEM, implement_prompt(by_name[name], error, code), component="p3.subset_exp"
                )
                code = extract_code(reply)
                if code is None:
                    error, code = "the reply had no Python code block defining decompose()", reply[-2000:]
                    attempts.append({"attempt": attempt, "error": error})
                    continue
                res, error = run_harness(deps, f"idea_{len(log) + 1}_{attempt}", code)
                attempts.append({"attempt": attempt, "error": error, "code": code})
                if error is None:
                    results[name] = res
                    break
            log[name] = {"ok": name in results, "attempts": attempts}
        artifact = _write_json(deps, "subset_exp", {"results": results, "log": log})
        if len(results) == 1:
            return {"artifacts": {"subset_exp_raw": artifact},
                    **_stop("subset_exp", "gate: no selected idea produced a valid run")}  # fmt: skip
        return {"results": results, "artifacts": {"subset_exp_raw": artifact}, "trail": ["subset_exp"]}

    return node


def results_gate_node(deps: LoopDeps) -> Callable[[dict], dict]:
    """Gate for the subset experiments: does an idea beat the baseline on every dataset, and which is best?

    `loop.best_method` is only asked when some idea beat the baseline everywhere, and not for a dataset on which
    the table's own numbers tie for best (there is no unique answer to ask the judge for): the first live run that
    reached this gate spent 6000 reasoning tokens on a tie and then failed closed."""

    def node(state: dict) -> dict:
        results = state["results"]
        shown = tables.valid_datasets(results, deps.datasets)
        ideas = [m for m in results if m != tables.BASELINE]
        verdicts, beat_all, unsure, first_gate = {}, {m: True for m in ideas}, [], None
        for m in ideas:
            for d in shown:
                q, material, shadow = questions.beats_baseline(m, d, results, deps.datasets, deps.n_seeds)
                v, confident = ask_gate(deps, "subset_exp", q, material, shadow, state)
                verdicts[f"beats_baseline:{m}:{d}"] = v.model_dump(mode="json")
                first_gate = first_gate or v
                unsure += [] if confident else [f"{q.id} {m} {d}"]
                beat_all[m] = beat_all[m] and confident and v.answer is True
        contenders = [m for m in ideas if beat_all[m]]
        wins, skipped = {m: 0 for m in results}, []
        for d in shown if contenders else []:
            q, material, shadow = questions.best_method(d, results, deps.datasets, deps.n_seeds)
            if shadow is None:
                skipped.append(d)
                continue
            v, confident = ask_gate(deps, "subset_exp", q, material, shadow, state)
            verdicts[f"best_method:{d}"] = v.model_dump(mode="json")
            if confident and v.answer in wins:
                wins[v.answer] += 1
            else:
                unsure.append(f"{q.id} {d}")
        best = max(contenders, key=lambda m: wins[m], default=None)  # the first contender on equal wins
        artifact = _write_json(deps, "results_gate", {"beats_all_datasets": beat_all, "wins": wins, "best": best,
                                                      "best_method_tied_not_asked": skipped})  # fmt: skip
        decision = "accept" if best else "reject"
        metrics = {"n_ideas_run": float(len(ideas)), "n_beating_baseline": float(len(contenders))}
        update: dict = {"verdicts": verdicts, "best": best, "artifacts": {"subset_exp": artifact},
                        "stage_results": [stage_result(deps, "subset_exp", artifact, first_gate, decision, metrics)],
                        "trail": ["results_gate"]}  # fmt: skip
        if unsure:
            reason = f"gate: the judge was not confident on {len(unsure)} question(s): {unsure[:3]}"
            update |= _stop("subset_exp", reason)
        return finish(update)

    return node

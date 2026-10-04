"""Offline fakes for the loop graph: a judge that reads the result table, a scripted generator, a fake sandbox.

Shared by tests/test_loop_stages.py and the kill-and-resume worker (tests/_loop_worker.py). Nothing here touches
the network or Docker.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from vera.ledger import CallResult, Ledger, metered_call
from vera.loop.stages import LoopDeps
from vera.sandbox import SandboxResult
from vera.schemas import Budget, OutputGuidance, ProblemSpec, Question, QuestionType, RunSpec, Verdict

REPO = Path(__file__).resolve().parents[1]
TARGET = json.loads((REPO / "docs" / "results" / "treehfd_baseline_target.json").read_text(encoding="utf-8"))


def ds(mean: float, std: float = 0.1, runtime: float = 5.0, valid: bool = True, reason: str | None = None,
       in_sample: float | None = None) -> dict:  # fmt: skip
    """One dataset's result in the harness's shape: `mean` is the held-out residual, `in_sample` the in-sample one."""
    if not valid:
        return {"valid": False, "invalid_reason": reason, "n_seeds": 3}
    ins = 0.6 * mean if in_sample is None else in_sample
    return {"valid": True, "invalid_reason": None, "n_seeds": 3,
            "residual_mse_pct": {"mean": mean, "std": std, "values": [mean] * 3},
            "residual_in_sample_pct": {"mean": ins, "std": std, "values": [ins] * 3},
            "runtime_s": {"mean": runtime, "std": 0.5, "values": [runtime] * 3}}  # fmt: skip


# Reproduction is judged per dataset as registered (paper: 2.0, tolerance 1.0): analytical on the held-out residual,
# airfoil on the in-sample one. The other column's value is far off in both, as measured, and must not matter.
BASELINE_OK = {"analytical": ds(2.4, in_sample=0.6), "airfoil": ds(4.7, in_sample=1.6)}
BASELINE_OFF = {"analytical": ds(2.4, in_sample=0.6), "airfoil": ds(4.7, in_sample=4.0)}  # airfoil in-sample outside
IDEAS = {  # what the scripted generator proposes
    "C1": ("shared knots", "Fit with shared knots."),
    "C2": ("ridge leaves", "Ridge-smooth the leaf values."),
    "C3": ("pruned pairs", "Keep only the top interactions."),
    "C4": ("deeper variables", "Select variables deeper in each tree."),
}
IDEA_SCORES = {"C1": 5, "C2": 4, "C3": 2, "C4": 3}
IDEA_RESULTS = {  # marker -> harness result for the idea (better = lower residual)
    "C1": {"analytical": ds(1.8), "airfoil": ds(2.2)},  # beats the baseline everywhere
    "C2": {"analytical": ds(2.9), "airfoil": ds(2.6)},  # worse on one dataset
}


GUIDANCE = OutputGuidance(
    max_words=400,
    required_sections=["Abstract", "Method", "Results", "Limitations", "References"],
    emphasis="Be plain about what was and was not established.",
    constraints=["forbid: state of the art"],
)
REFS = [
    {"key": "R1", "title": "Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD "
     "Algorithm", "authors": ["Clement Benard"], "year": "2025", "id": "arXiv:2510.24815",
     "url": "https://arxiv.org/abs/2510.24815", "source": "arxiv", "retrieved": "2026-10-01"},
    {"key": "R2", "title": "XGBoost: A Scalable Tree Boosting System", "authors": ["Tianqi Chen", "Carlos Guestrin"],
     "year": "2016", "id": "arXiv:1603.02754", "url": "https://arxiv.org/abs/1603.02754", "source": "arxiv",
     "retrieved": "2026-10-01"},
]


def paper(extra: str = "", words: int = 120, sections: tuple = ("Abstract", "Method", "Results", "Limitations")) -> str:
    """A compliant draft (the model's own text: no table, no reference list), with optional extra text."""
    parts = []
    for s in sections:
        body = "We study TreeHFD [R1] on xgboost models [R2]. " + ("word " * (words // len(sections)))
        if s == "Results":
            body += "\n\n[[RESULTS_TABLE]]\n"
        parts.append(f"## {s}\n\n{body}")
    return "\n\n".join(parts) + "\n" + extra


def make_spec(run_id: str = "fake-run", max_usd: float = 3.0, max_wall: int = 7200) -> RunSpec:
    return RunSpec(
        run_id=run_id,
        problem=ProblemSpec(
            parent_id="2510.24815", repo_url="https://github.com/ThalesGroup/treehfd", repo_commit="a" * 40,
            metric="residual_mse_pct", datasets=["analytical", "airfoil"],
            subset={"n_seeds": 3, "n_ideas": 4, "n_run": 2},
        ),
        guidance=GUIDANCE,
        budget=Budget(max_usd=max_usd, max_wall_seconds=max_wall),
        models={"ideate": "fake-gen", "subset_exp": "fake-gen"},
    )  # fmt: skip


def parse_table(material: str) -> tuple[list[str], dict[str, list[float]]]:
    """(header cells, method -> mean per column) from the markdown table in a gate's material."""
    rows = [ln for ln in material.splitlines() if ln.startswith("|") and not ln.startswith("|---")]
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    table = {}
    for ln in rows[1:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        table[cells[0]] = [float(c.split("±")[0]) for c in cells[1:]]
    return header, table


class FakeJudge:
    """Answers by reading the material, as a correct judge would; `overrides` forces answers by question id."""

    def __init__(self, ledger: Ledger | None = None, budget: Budget | None = None, *, overrides: dict | None = None,
                 confidence: float = 0.9, judge_id: str = "p2.judge", scores: dict | None = None,
                 low_confidence_for: set | None = None) -> None:  # fmt: skip
        self.ledger, self.budget, self.overrides, self.confidence = ledger, budget, overrides or {}, confidence
        self.judge_id, self.scores = judge_id, scores or IDEA_SCORES
        self.low = low_confidence_for or set()
        self.asked: list[str] = []

    def _answer(self, q: Question, material: str):
        if q.id in self.overrides:
            return self.overrides[q.id]
        if q.id == "loop.baseline_reproduced":
            header, table = parse_table(material)
            row = table["TreeHFD (baseline)"]
            tol = float(re.search(r"Tolerance: ([\d.]+)", material).group(1))
            refs = re.findall(r"(\w+) ([\d.]+) \(compare the (in-sample|held-out) column\)", material)
            ok = True
            for dataset, ref, basis in refs:
                name = f"{dataset} · Residual MSE, {basis} (%) ↓"
                ok = ok and name in header and abs(row[header.index(name) - 1] - float(ref)) <= tol + 1e-9
            return ok and len(refs) == len(TARGET["datasets"])
        if q.id == "loop.guidance_met":
            return True
        if q.id == "loop.idea_worth_run":
            return self.scores[re.search(r'idea "(C\d+)', q.text).group(1)]
        header, table = parse_table(material)
        if q.id == "loop.beats_baseline":
            method = re.search(r'Does "(.*?)" beat', q.text).group(1)
            dataset = re.search(r"for the (\w+) dataset", q.text).group(1)
            col = header.index(f"{dataset} · Residual MSE (%) ↓") - 1
            return table[method][col] < table["TreeHFD (baseline)"][col]
        if q.id == "loop.best_method":
            dataset = re.search(r"on the (\w+) dataset", q.text).group(1)
            col = header.index(f"{dataset} · Residual MSE (%) ↓") - 1
            return min(table, key=lambda m: table[m][col])
        raise AssertionError(f"unexpected question {q.id}")

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        out = []
        for q in questions:
            self.asked.append(q.id)
            if self.ledger is not None and self.budget is not None:
                metered_call(lambda: CallResult(text="x", model="fake-judge", cost_usd=0.0001), ledger=self.ledger,
                             budget=self.budget, component="p2.judge", backend="fake", model="fake-judge",
                             estimate_usd=0.0001)  # fmt: skip
            out.append(Verdict(question_id=q.id, answer=self._answer(q, state),
                               confidence=0.4 if q.id in self.low else self.confidence,
                               confidence_source="self_report", backend="fake", escalated=False, cost_usd=0.0001,
                               latency_ms=1, trace_id="t", judge_id=self.judge_id))  # fmt: skip
        return out


class FakeGenerator:
    """Proposes IDEAS, then returns a code block carrying the idea's marker. `fail_first` makes an idea's first
    attempt fail in the sandbox; `crash_on` runs a callback before the n-th implementation call."""

    def __init__(self, ledger: Ledger, budget: Budget, *, cost: float = 0.01, no_code: set | None = None,
                 on_implement=None, ideas: dict | None = None, ablate: bool = False) -> None:  # fmt: skip
        self.ledger, self.budget, self.cost, self.ablate = ledger, budget, cost, ablate
        self.no_code, self.on_implement, self.ideas = no_code or set(), on_implement, ideas or IDEAS
        self.calls: list[str] = []
        self.implemented = 0
        self.drafts: list[str] = []  # write-up replies to give in order; the last repeats

    def generate(self, system: str, prompt: str, *, component: str) -> str:
        self.calls.append(component)
        marker = None
        if component == "p3.subset_exp":
            marker = re.search(r"Idea: (C\d+)", prompt).group(1)
            self.implemented += 1
            if self.on_implement:
                self.on_implement(self.implemented)
        text = self._text(component, marker)
        reply = metered_call(lambda: CallResult(text=text, model="fake-gen", cost_usd=self.cost),
                             ledger=self.ledger, budget=self.budget, component=component, backend="fake",
                             model="fake-gen", estimate_usd=self.cost)  # fmt: skip
        return reply.text

    def _text(self, component: str, marker: str | None) -> str:
        if component == "p3.ideate":
            items = [{"name": n, "description": d} for n, d in self.ideas.values()]
            return "Here are the ideas:\n```json\n" + json.dumps(items) + "\n```"
        if component == "p3.ablation":
            return "```json\n" + json.dumps(ABLATION_VARIANTS) + "\n```" if self.ablate else "No ablation."
        if component == "p3.write_up":
            return self.drafts.pop(0) if len(self.drafts) > 1 else (self.drafts[0] if self.drafts else paper())
        if marker in self.no_code:
            return "I cannot do that."
        return f"```python\n# IDEA:{marker}\ndef decompose(model, X_train, X_test):\n    return 0.0, {{}}\n```"


class FakeSandbox:
    """Stands in for `vera.sandbox.run_script`: writes the harness's result.json for the method in the driver.

    `ideas`: marker -> dataset results, or a list of them (one per attempt; an `{"error": ...}` entry makes the
    method raise). `baseline`: the baseline's dataset results, or None to make the harness fail."""

    def __init__(self, baseline: dict | None = None, ideas: dict | None = None, seconds: int = 1) -> None:
        self.baseline = BASELINE_OK if baseline is None else baseline
        self.ideas = {k: list(v) if isinstance(v, list) else [v] for k, v in (ideas or IDEA_RESULTS).items()}
        self.seconds, self.calls, self.fail_baseline = seconds, [], False

    def __call__(self, source: str, workdir: Path, *, limits=None, budget: Budget | None = None, **_):
        if budget is not None:
            budget.charge(0.0, seconds=self.seconds, calls=0)
        is_idea = "/work/method.py" in source
        self.calls.append("idea" if is_idea else "baseline")
        if is_idea:
            marker = re.search(r"# IDEA:(\w+)", (workdir / "method.py").read_text(encoding="utf-8")).group(1)
            queue = self.ideas[marker]
            result = queue.pop(0) if len(queue) > 1 else queue[0]
        else:
            result = self.baseline
        out = {"method": "x"}
        if self.fail_baseline and not is_idea:
            return SandboxResult(1, "", "boom", False, False, 1.0, 0.0, False, False, None, "fake")
        if "error" in result:
            out["error"] = result["error"]
        else:
            out["datasets"] = result
        (workdir / "result.json").write_text(json.dumps(out), encoding="utf-8")
        return SandboxResult(0, "ok", "", False, False, 1.0, 0.0, False, False, None, "fake")


def make_deps(tmp_path: Path, *, judge=None, generator=None, sandbox=None, spec: RunSpec | None = None,
              run_id: str = "fake-run", ledger: Ledger | None = None,
              budget: Budget | None = None) -> LoopDeps:  # fmt: skip
    spec = spec or make_spec(run_id)
    budget = budget or spec.budget.model_copy()
    ledger = ledger or Ledger(tmp_path / f"run_{run_id}.jsonl", run_id=run_id)
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    (run_dir / "retrieved.jsonl").write_text("".join(json.dumps(r) + "\n" for r in REFS), encoding="utf-8")
    data = tmp_path / "datasets"
    data.mkdir(exist_ok=True)
    (data / "airfoil_self_noise.dat").write_text("1 2 3 4 5 6\n")
    return LoopDeps(
        spec=spec, target=TARGET, generator=generator or FakeGenerator(ledger, budget),
        judge=judge or FakeJudge(ledger, budget), sandbox=sandbox or FakeSandbox(), budget=budget,
        run_dir=tmp_path / "run", data_dir=data, ledger=ledger, extra={"lookup": lambda title: []},
    )  # fmt: skip


def question_for_tests() -> Question:
    return Question(id="loop.x", type=QuestionType.BOOLEAN, text="?")


ABLATION_VARIANTS = [  # what the scripted generator answers when asked to ablate the winning idea
    {"component": "shared knots", "code": "# IDEA:A1\ndef decompose(model, X_train, X_test):\n    return 0.0, {}\n"},
    {"component": "refit step", "code": "# IDEA:A2\ndef decompose(model, X_train, X_test):\n    return 0.0, {}\n"},
]

"""The parent problem a loop run works on: its harness, metrics, interface and prompt text (Increment 4).

Increments 2 and 3 ran the loop on one problem, TreeHFD, and the stages carried its wording. A second problem (the
credal ambiguity sets) needs the same stages with its own harness, metrics and interface, so what is specific to a
problem lives in a `ProblemKit`, and the stages read the *active* kit (TreeHFD unless a run script says otherwise with
`use`). The default behaviour of every stage is unchanged: the TreeHFD kit holds the values the stages used before.

A kit has no logic of its own beyond text and small builders: the gates, the stopping rule and the audit are the same
for every problem.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from vera.loop import tables
from vera.sandbox import SandboxLimits

REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProblemKit:
    id: str
    method_name: str  # the parent's method, as the text calls it ("TreeHFD", "LV")
    baseline_label: str  # the baseline's row name in every table
    function_name: str  # the interface function an idea defines ("decompose", "fit_predict")
    harness_dir: Path
    metrics: tuple[tuple[str, str], ...]  # (results key, column name); every metric is lower-is-better
    primary: str
    image: str | None = None  # the sandbox image (None: the sandbox default, the TreeHFD image)
    baseline_limits: SandboxLimits | None = None  # the baseline run may need more than an idea's run
    experiment_limits: SandboxLimits | None = None
    repro_metrics: tuple[tuple[str, str], ...] = ()
    repro_metric: str = ""  # the metric a reproduction is compared on when the target names one
    # text and builders; None means the stage's own (TreeHFD) text
    ideate_system: str | None = None
    ideate_prompt: Callable | None = None  # (deps, baseline_table, n) -> str
    implement_prompt: Callable | None = None  # (idea, error, previous) -> str
    idea_worth_run: Callable | None = None  # (name, description, baseline_table) -> (Question, material)
    baseline_reproduced: Callable | None = None  # (target, results, n_seeds, datasets) -> (Question, material, shadow)
    baseline_example: Callable | None = None  # () -> source shown as the interface example
    writeup_intro: str | None = None  # opening of the write-up prompt
    writeup_limits: str | None = None  # what the limits paragraph must name
    extra: dict = field(default_factory=dict)

    @property
    def metric_names(self) -> dict[str, str]:
        return dict(self.metrics)


TREEHFD = ProblemKit(
    id="treehfd",
    method_name="TreeHFD",
    baseline_label=tables.BASELINE,
    function_name="decompose",
    harness_dir=REPO / "docker" / "sandbox-treehfd",
    metrics=tables.METRICS,
    primary=tables.PRIMARY,
    repro_metrics=tables.REPRO_METRICS,
    repro_metric=tables.REPRO_METRIC,
)

_active: ProblemKit = TREEHFD


def active() -> ProblemKit:
    return _active


def use(kit: ProblemKit) -> ProblemKit:
    """Make `kit` the problem the loop stages and tables work on; returns the previous kit."""
    global _active
    previous, _active = _active, kit
    tables.BASELINE = kit.baseline_label
    tables.METRICS = kit.metrics
    tables.PRIMARY = kit.primary
    tables.METRIC_NAME = dict(kit.metrics)
    tables.REPRO_METRICS = kit.repro_metrics
    tables.REPRO_METRIC = kit.repro_metric
    tables.PROBLEM_NAME = kit.method_name
    return previous


@contextlib.contextmanager
def using(kit: ProblemKit) -> Iterator[ProblemKit]:
    previous = use(kit)
    try:
        yield kit
    finally:
        use(previous)

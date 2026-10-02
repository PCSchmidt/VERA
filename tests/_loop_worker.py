"""Subprocess worker for the loop's kill-and-resume test (not a test module).

Runs the loop graph with the offline fakes in tests/loop_fakes.py. `start` begins a run; with a crash index N the
process dies (os._exit, no cleanup) on entering the N-th implementation call, as a killed run would. `resume`
continues from the last checkpoint. Run directory, checkpoints and the run's one ledger live under <dir>.

Usage: python _loop_worker.py <dir> start|resume [crash_at]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.loop_fakes import FakeGenerator, FakeJudge, FakeSandbox, make_deps, make_spec  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.loop.graph import run_loop  # noqa: E402


def main() -> None:
    root, mode = Path(sys.argv[1]), sys.argv[2]
    crash_at = int(sys.argv[3]) if len(sys.argv) > 3 else None
    spec = make_spec("kill-run")
    budget = spec.budget.model_copy()
    ledger = Ledger(root / "run_kill-run.jsonl", run_id="kill-run")

    def maybe_crash(n: int) -> None:
        if crash_at is not None and n == crash_at:
            os._exit(3)

    generator = FakeGenerator(ledger, budget, on_implement=maybe_crash)
    deps = make_deps(root, spec=spec, ledger=ledger, budget=budget, generator=generator,
                     judge=FakeJudge(ledger, budget), sandbox=FakeSandbox())  # fmt: skip
    state = run_loop(deps, resume_run=(mode == "resume"))
    print(f"best={state['best']} trail={','.join(state['trail'])}")


if __name__ == "__main__":
    main()

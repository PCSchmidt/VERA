"""A Budget that also honours the user's Stop button.

The app asks a run to stop by creating a file in its directory. The next charge (every model call and every sandbox
run is charged first) raises `BudgetExceeded`, which the stage guards already turn into a clean stop with a best-so-far
report: the ledger stays consistent, because nothing is charged for a call that was not made.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import PrivateAttr

from vera.schemas import Budget, BudgetExceeded

STOP_FILE = "STOP"


class AppBudget(Budget):
    _stop_file: Path | None = PrivateAttr(default=None)

    def watch(self, run_dir: Path) -> AppBudget:
        self._stop_file = run_dir / STOP_FILE
        return self

    def charge(self, usd: float, seconds: int = 0, calls: int = 1) -> None:
        if self._stop_file is not None and self._stop_file.exists():
            raise BudgetExceeded("stopped by the user")
        super().charge(usd, seconds, calls)

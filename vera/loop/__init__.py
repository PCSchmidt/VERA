"""The research loop (P3): stages, gates and the budget stop. Increment 2 builds it up feature by feature."""

from __future__ import annotations

# The questions the loop asks the judge. Every id starts with "loop." and goes straight to GLM (T1 decision,
# docs/04): the loop asks few, and Jev missed 4 of 39 loop-gate test items. `vera.judge.cheap_path` routes on the
# prefix, so a new loop question cannot reach Jev by being left out of this set.
LOOP_PREFIX = "loop."
# The literature stage's questions (Increment 3). Until the claim-support benchmark has dev results (SPEC, "Synthesis"),
# no `lit.*` question reaches Jev: they go straight to GLM like the loop's, the safe default for judgments nobody has
# measured the cheap path on. The routing is then chosen on dev only.
LIT_PREFIX = "lit."
LOOP_QUESTION_IDS: frozenset[str] = frozenset(
    {
        "loop.baseline_reproduced",  # Boolean: do the reproduced numbers match the reference within tolerance?
        "loop.idea_worth_run",  # Score: is this idea worth a subset run?
        "loop.beats_baseline",  # Boolean: does the idea's result beat the baseline on the metric?
        "loop.best_method",  # Choice: which method has the best mean on a dataset? (benchmark wording)
        "loop.guidance_met",  # Boolean: does the write-up follow the output guidance?
    }
)

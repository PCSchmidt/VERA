# ruff: noqa: E501
"""Gate `problem2_ready`: the second parent problem, its registered target, its harness variants and what they cost (Increment 4).

Requires:
- docs/results/problem2_feasibility.md (the feasibility note written before the target);
- docs/results/credal_baseline_target.json with the SHA-256 in credal_baseline_target.sha256, registered before the first baseline
  attempt recorded in data/results/credal_baseline_1.json (the target is from the parent paper only: its `note` says so);
- data/results/credal_baseline_1.json: a baseline of the parent's own experiment with the registered number of replications for
  all five methods, the LV means within the registered relative tolerance of the paper on every metric and LV best of the five (or a
  stated, evidenced failure: `all_within_tolerance` false with the attempts listed), and the attempts with what each exposed;
- both harness variants built: docker/sandbox-credal/harness.py (by hand) and generic_harness.py (T10 option (c)), the Dockerfile
  and the solver patch;
- the effort of each recorded: docs/results/problem2_effort.json (by-hand hours with their start and end, the number of attempts
  and image builds; the adapter trial's attempts, model cost, wall time and accepted-or-not), and data/results/t10_adapter_trial.json
  with the baseline gate's verdicts when an adapter was accepted.
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    res = args.root / "docs" / "results"
    if not (res / "problem2_feasibility.md").exists():
        block("docs/results/problem2_feasibility.md not found")
    target_file = res / "credal_baseline_target.json"
    target = load(target_file, "the registered target")
    recorded = (res / "credal_baseline_target.sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(target_file.read_bytes()).hexdigest() != recorded:
        block("the registered target changed after its hash was recorded")
    if "parent paper only" not in target["note"] and "parent paper" not in target["note"]:
        block("the target's note must say its values are from the parent paper only")
    base = load(args.root / "data" / "results" / "credal_baseline_1.json", "the baseline reproduction")
    if target["registered"] >= base["first_attempt_started"]:
        block("the target was not registered before the first baseline attempt")
    if base["n_replications"] != target["experiment"]["n_replications"]:
        block("the baseline does not have the registered number of replications")
    if not (base["all_within_tolerance"] and base["lv_best_on_all_four"]) and not base.get("attempts"):
        block("the baseline is outside tolerance with no stated, evidenced failure")
    if not base["attempts"]:
        block("the attempts (and what each exposed) are not recorded")
    for name in ("harness.py", "generic_harness.py", "Dockerfile", "patch_solver.py"):
        if not (args.root / "docker" / "sandbox-credal" / name).exists():
            block(f"docker/sandbox-credal/{name} not found")
    effort = load(res / "problem2_effort.json", "the effort record")
    for key in ("by_hand", "adapter_trial"):
        if key not in effort:
            block(f"problem2_effort.json lacks {key}")
    by_hand = effort["by_hand"]
    if not all(k in by_hand for k in ("hours", "started", "finished", "attempts", "image_builds")):
        block("the by-hand effort must record hours, start, finish, attempts and image builds")
    trial = load(args.root / "data" / "results" / "t10_adapter_trial.json", "the adapter trial")
    if not trial.get("attempts") or "model_cost_usd" not in trial or "generic_share_of_by_hand_pct" not in trial:
        block("the adapter trial lacks attempts, model cost or the generic share")
    if trial["accepted"] and not trial.get("gate"):
        block("an accepted adapter needs the baseline gate's verdicts")
    ok(f"target registered {target['registered']} before the first attempt; baseline within tolerance: {base['all_within_tolerance']}, "
       f"LV best: {base['lv_best_on_all_four']}; by hand {by_hand['hours']} h over {len(base['attempts'])} attempts; adapter trial "
       f"{'accepted' if trial['accepted'] else 'not accepted'} in {len(trial['attempts'])} attempts at ${trial['model_cost_usd']}")


if __name__ == "__main__":
    main()

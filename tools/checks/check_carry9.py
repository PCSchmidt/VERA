# ruff: noqa: E501
"""Increment 9 checks, by part (SPEC.md). Exit 0 passes, exit 2 blocks.

--part unsure  (gate `unsure_rule_ready`): the audit settles every judge failure with one function (`disagreement.outcome`):
               a confident reference no fails, a confident yes is a disagreement, an answer below the threshold either
               way is unsettled; the offline re-read of Increment 8's five re-audits exists and reproduces from the stored
               files with no verdict changed; the reader and PDF list unsettled items apart; AUD-F-14 tests exist; the
               earlier freezes hold.
--part write   (gate `write_confirm_ready`): the write step (the review's and the paper's `verify_sentences`, and the
               interpretation stage) confirms a cheap confident no with the reference; the app gives the write step its
               reference; RSH-F-17 tests exist; the earlier freezes hold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _common import block, ok, repo_root_arg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_carry6 import frozen_unchanged, has_tests  # noqa: E402
from check_carry7 import inference_hash_holds  # noqa: E402
from check_carry8 import realcase_hash_holds  # noqa: E402


def freezes(root: Path) -> str:
    return f"audit files unchanged ({frozen_unchanged(root)}); {inference_hash_holds(root)}; {realcase_hash_holds(root)}"


def part_unsure(root: Path) -> None:
    text = (root / "vera" / "audit" / "disagreement.py").read_text(encoding="utf-8")
    if "def outcome(" not in text or "UNSETTLED" not in text or "kind, why = outcome(" not in text:
        block("the audit does not settle judge failures with disagreement.outcome")
    sys.path.insert(0, str(root / "scripts"))
    import reread9  # noqa: PLC0415

    stored = root / "data" / "results" / "reread9.json"
    if not stored.exists():
        block("no offline re-read (scripts/reread9.py)")
    result = json.loads(stored.read_text(encoding="utf-8"))
    for label in reread9.PAPERS:
        report = json.loads((root / "data" / "reaudit8" / label / "audit_report.json").read_text(encoding="utf-8"))
        after, _ = reread9.reread(report["findings"])
        if reread9.tally(after) != result["papers"][label]["after"]:
            block(f"{label}: the re-read does not reproduce from the stored re-audit")
    for rel, needle in (("vera/app/static/app.js", 'class: "unsettled"'), ("vera/app/pdf.py", "Unsettled (")):
        if needle not in (root / rel).read_text(encoding="utf-8"):
            block(f"{rel} does not list unsettled items apart")
    n = has_tests(root, "AUD-F-14", 5)
    moved = sum(p["after"]["unsettled"] for p in result["papers"].values())
    ok(f"symmetric rule in the audit; re-read reproduces ({moved} failures now unsettled); {n} AUD-F-14 tests; {freezes(root)}")


def part_write(root: Path) -> None:
    lit = root / "vera" / "literature"
    if not (lit / "confirm.py").exists():
        block("vera/literature/confirm.py not found")
    for name in ("synthesis_stage.py", "paper_interpret.py"):
        if "confirm.confirm_no(" not in (lit / name).read_text(encoding="utf-8"):
            block(f"{name} does not confirm a cheap no with the reference")
    if 'deps.extra["reference"] = confirmer(' not in (root / "vera" / "app" / "pipeline.py").read_text(encoding="utf-8"):
        block("the app does not give the write step its reference")
    n = has_tests(root, "RSH-F-17", 5)
    ok(f"write step confirms with the reference (review, paper, interpretation); {n} RSH-F-17 tests; {freezes(root)}")


PARTS = {"unsure": part_unsure, "write": part_write}


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--part", choices=sorted(PARTS), required=True)
    args = parser.parse_args()
    PARTS[args.part](args.root)


if __name__ == "__main__":
    main()

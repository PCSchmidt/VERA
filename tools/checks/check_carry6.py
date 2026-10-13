# ruff: noqa: E501
"""Increment 6 checks, by part (SPEC.md). Exit 0 passes, exit 2 blocks.

--part evidence  (gate `evidence_ready`): the wider-evidence module and its RSH-F-14 tests exist, its limits are the SPEC's
                 (15 papers in full, 10 passages each), and no audit file frozen at Increment 5's scoping has changed.
--part inference_frozen  (gate `inference_set_frozen`): the seeded inference set exists with its counts, its test split
                 and the check's source are hashed and the hashes still hold, and any test result was run after the freeze.
--part inference_measured  (gate `inference_measured`): the one test run exists, ran on the frozen hashes after the freeze,
                 reports every rate with its interval, and its spend (from its ledger) is within the $1 cap.
--part app       (gate `app_paper_ready`): the review-paper routes, the button and reader in the front end (hidden in the
                 static showcase), APP-F-04 tests, real PNG screenshots of the paper pages, and no frozen file changed.
--part paper     (gate `paper_stage_ready`): the paper stage's modules exist, the review and the paper share one verify
                 function, the paper's producer is not a judge, RSH-F-12 tests exist, and no frozen file has changed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from _common import block, ok, repo_root_arg

FROZEN = Path("data") / "results" / "audit_hash_incr5.json"


def frozen_unchanged(root: Path) -> str:
    """The Increment 5 freeze hash, recomputed the way check_carry5 computes it; blocks if it differs."""
    frozen = json.loads((root / FROZEN).read_text(encoding="utf-8"))
    h = hashlib.sha256()
    for rel in sorted(frozen["files"]):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    if h.hexdigest() != frozen["sha256"]:
        block(
            "an audit file frozen at Increment 5's scoping has changed; Increment 6 changes none (SPEC: stop and ask first)"
        )
    return frozen["sha256"][:12]


def has_tests(root: Path, req: str, min_count: int = 1) -> int:
    pattern = re.compile(rf"def test_{req.replace('-', '_')}_")
    n = sum(len(pattern.findall(p.read_text(encoding="utf-8"))) for p in (root / "tests").rglob("test_*.py"))
    if n < min_count:
        block(f"no test named test_{req.replace('-', '_')}_... (need {min_count})")
    return n


def part_evidence(root: Path) -> None:
    module = root / "vera" / "literature" / "paper_evidence.py"
    if not module.exists():
        block("vera/literature/paper_evidence.py not found")
    text = module.read_text(encoding="utf-8")
    if not re.search(r"^PAPER_READ_TOP = 15\b", text, re.M) or not re.search(
        r"^PAPER_PASSAGES_PER_PAPER = 10\b", text, re.M
    ):
        block("the paper's reading limits are not the SPEC's (15 papers in full, 10 passages each)")
    n = has_tests(root, "RSH-F-14", 3)
    digest = frozen_unchanged(root)
    ok(f"wider evidence present with SPEC limits; {n} RSH-F-14 tests; audit files unchanged ({digest})")


def part_paper(root: Path) -> None:
    lit = root / "vera" / "literature"
    for name in ("paper.py", "paper_stage.py"):
        if not (lit / name).exists():
            block(f"vera/literature/{name} not found")
    stage = (lit / "paper_stage.py").read_text(encoding="utf-8")
    if "verify_sentences(" not in stage or "def verify_sentences(" not in (lit / "synthesis_stage.py").read_text(
        "utf-8"
    ):
        block("the paper's evidence sections must go through the review's own verify_sentences")
    if 'COMPONENT = "p3.paper.write"' not in stage:
        block("the paper's producer id is not p3.paper.write")
    pipeline = (root / "vera" / "app" / "pipeline.py").read_text(encoding="utf-8")
    if "def run_paper(" not in pipeline or "def resume_paper(" not in pipeline:
        block("the app pipeline has no run_paper/resume_paper")
    n = has_tests(root, "RSH-F-12", 6)
    digest = frozen_unchanged(root)
    ok(
        f"paper stage present, shared verify, producer p3.paper.write; {n} RSH-F-12 tests; audit files unchanged ({digest})"
    )


def _freeze(root: Path) -> tuple[dict, dict]:
    sys.path.insert(0, str(root / "scripts"))
    import measure_inference as mi  # noqa: PLC0415 - the hashes are computed exactly as the measurement computes them

    path = root / "data" / "results" / "inference_hash_incr6.json"
    if not path.exists():
        block("data/results/inference_hash_incr6.json not found (scripts/measure_inference.py freeze)")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    if frozen["test_sha256"] != mi.test_hash():
        block("the inference test split changed after the freeze")
    if frozen["check_sha256"] != mi.check_hashes():
        block("the inference check's source changed after the freeze")
    return frozen, {"cap": mi.CAP_USD}


def part_inference_frozen(root: Path) -> None:
    meta = json.loads((root / "data" / "seeded_inference" / "meta.json").read_text(encoding="utf-8"))
    n_test = sum(meta["counts"]["test"].values())
    if n_test < 60 or meta["counts"]["test"]["control"] < 10:
        block(f"the test split has {n_test} items and {meta['counts']['test']['control']} controls (need 60 and 10)")
    frozen, _ = _freeze(root)
    result = root / "data" / "results" / "inference_incr6_test.json"
    if result.exists() and json.loads(result.read_text(encoding="utf-8"))["run_at"] <= frozen["frozen_at"]:
        block("a test result predates the freeze")
    n13, n11 = has_tests(root, "RSH-F-13", 3), has_tests(root, "AUD-F-11", 2)
    digest = frozen_unchanged(root)
    ok(
        f"inference set frozen at {frozen['frozen_at']} ({n_test} test items); {n13} RSH-F-13 and {n11} AUD-F-11 tests; "
        f"audit files unchanged ({digest})"
    )


def part_inference_measured(root: Path) -> None:
    frozen, limits = _freeze(root)
    path = root / "data" / "results" / "inference_incr6_test.json"
    if not path.exists():
        block("no test result (scripts/measure_inference.py test)")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["run_at"] <= frozen["frozen_at"] or result["test_sha256"] != frozen["test_sha256"]:
        block("the test result was not run on the frozen set after the freeze")
    s = result["summary"]
    for key in ("false_positive_on_controls", "judge_layer_detection", "rules_layer_detection"):
        if s[key]["n"] == 0 or len(s[key]["ci95"]) != 2:
            block(f"{key} is missing its count or interval")
    ledgers = sorted((root / "data" / "ledger").glob("inference_incr6_*.jsonl"))
    spent = sum(
        json.loads(ln)["cost_usd"] for p in ledgers for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()
    )
    if spent > limits["cap"]:
        block(f"the measurement spent ${spent:.4f}, over its ${limits['cap']:.2f} cap")
    j, fp = s["judge_layer_detection"], s["false_positive_on_controls"]
    ok(
        f"judge layer caught {j['k']}/{j['n']} ({j['ci95'][0]:.0%}-{j['ci95'][1]:.0%}); false positives {fp['k']}/{fp['n']} "
        f"({fp['ci95'][0]:.0%}-{fp['ci95'][1]:.0%}); spend ${spent:.4f}"
    )


PAPER_SHOTS = ["paper-light", "paper-dark", "paper-narrow", "makepaper-light"]


def part_app(root: Path) -> None:
    server = (root / "vera" / "app" / "server.py").read_text(encoding="utf-8")
    for route in (
        '/review-paper"',
        "/review-paper/status",
        "/review-paper/stop",
        "/review-paper/resume",
        "/review-paper/pdf",
    ):
        if route not in server:
            block(f"the server has no {route.strip(chr(34))} route")
    js = (root / "vera" / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for needle in (
        "Make a paper from this review",
        "makePaperView",
        "paperRunView",
        'class: "interp"',
        "not checked against quotes",
    ):
        if needle not in js:
            block(f"the front end lacks {needle!r}")
    if "make-paper\\/|paper-run\\/|paper\\/" not in js:
        block("the static showcase does not send the paper routes to 'Run it yourself'")
    for name in PAPER_SHOTS:
        f = root / "docs" / "screenshots" / f"{name}.png"
        if not f.exists() or not f.read_bytes().startswith(b"\x89PNG"):
            block(f"screenshot {name}.png is missing or not a real PNG (scripts/screenshot_paper.py)")
    n = has_tests(root, "APP-F-04", 4)
    digest = frozen_unchanged(root)
    ok(
        f"review-paper routes, button, reader and form present; {n} APP-F-04 tests; {len(PAPER_SHOTS)} screenshots; "
        f"audit files unchanged ({digest})"
    )


def main() -> None:
    ap = repo_root_arg(__doc__)
    ap.add_argument(
        "--part", required=True, choices=["evidence", "paper", "inference_frozen", "inference_measured", "app"]
    )
    args = ap.parse_args()
    {
        "evidence": part_evidence,
        "paper": part_paper,
        "inference_frozen": part_inference_frozen,
        "inference_measured": part_inference_measured,
        "app": part_app,
    }[args.part](args.root)


if __name__ == "__main__":
    main()

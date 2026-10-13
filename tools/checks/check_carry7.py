# ruff: noqa: E501
"""Increment 7 checks, by part (SPEC.md). Exit 0 passes, exit 2 blocks.

--part sentences  (gate `sentence_checks_ready`): the sentence-status module has the SPEC's five rules and two judge
                  questions; the review and the paper share `verify_sentences`, which uses them; both drafting prompts ask
                  for typed sentences; RSH-F-15 tests exist; no file frozen at Increment 5 has changed, and the files
                  hashed for Increment 6's inference measurement still hash as they did (that result stays reproducible).

--part realcase   (gate `realcase_labelled`, human): the real-case set exists with the SPEC's counts (about 90 test items,
                  every named item in), and the reference labels cover every test item, were chosen by someone other than
                  the checks' author (no Claude model), after the set was built, from the sheet as built. The SPEC has
                  Chris label; on 2026-10-13 Chris kept labels chosen by ChatGPT instead (recorded in the labels file).

--part audit      (gate `audit_sentences_ready`): the sentence audit module exists and both audits (review and paper)
                  run it; the PDF and the reader say what green covers when it ran, list synthesis sentences and mark
                  repeated quotes; the reader marks synthesis in the text; AUD-F-12 tests exist; screenshots are PNGs;
                  both freezes hold.

--part measured   (gate `checks_measured`): the freeze (test items, their labels, every check's source) predates the one
                  test run, still holds, and that run reports old and new checks for each item type with intervals;
                  its spend, from its ledger, and the dev runs' are within the $1 cap.

--part coverage   (gate `coverage_search_ready`): the targeted search exists with the SPEC's limit (3 lookups), runs in the
                  paper's widening step before the evidence is widened, reads found works into the paper's evidence
                  without changing the review's records, and the threats section states what was searched for;
                  RSH-F-16 tests exist; both freezes hold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _common import block, ok, repo_root_arg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_carry6 import frozen_unchanged, has_tests  # noqa: E402 - the same freeze rule and test counting

RULES = ("def agreement_problem(", "def absence_problem(", "def names_a_source(", "def leans_on_context(",
         "def widen_quote(", "def mark_same_quotes(")  # fmt: skip
QUESTIONS = ('"claim.within_quote"', '"sentence.no_fact"')


def inference_hash_holds(root: Path) -> str:
    """The files hashed before Increment 6's inference test run still hash the same, so that measurement can be re-run."""
    sys.path.insert(0, str(root / "scripts"))
    import measure_inference as mi  # noqa: PLC0415

    frozen = json.loads((root / "data" / "results" / "inference_hash_incr6.json").read_text(encoding="utf-8"))
    if frozen["check_sha256"] != mi.check_hashes():
        block("a file hashed for Increment 6's inference measurement changed (anchoring.py, synthesis.py, inference.py); put new rules in new modules")
    return "inference files unchanged"


def part_sentences(root: Path) -> None:
    lit = root / "vera" / "literature"
    module = lit / "sentence_checks.py"
    if not module.exists():
        block("vera/literature/sentence_checks.py not found")
    text = module.read_text(encoding="utf-8")
    missing = [r for r in RULES + QUESTIONS + ("SENTENCE_RULE",) if r not in text]
    if missing:
        block(f"sentence_checks.py lacks {missing}")
    stage = (lit / "synthesis_stage.py").read_text(encoding="utf-8")
    for needed in ("sentence_checks.SENTENCE_RULE", "sentence_checks.parse_typed", "sentence_checks.within_quote",
                   "sentence_checks.no_fact", "sentence_checks.check_statement(",
                   "sentence_checks.sentence_records"):  # fmt: skip
        if needed not in stage:
            block(f"synthesis_stage.py does not use {needed}")
    paper_stage = (lit / "paper_stage.py").read_text(encoding="utf-8")
    if "verify_sentences(" not in paper_stage or "sentence_checks.sentence_records" not in paper_stage:
        block("the paper must go through verify_sentences and record its sentences")
    if "sentence_checks.SENTENCE_RULE" not in (lit / "paper.py").read_text(encoding="utf-8"):
        block("the paper's section prompt does not ask for typed sentences")
    if "sentence_checks.check_statement(" not in (lit / "paper_interpret.py").read_text(encoding="utf-8"):
        block("interpretation statements are not held to the agreement rule")
    n = has_tests(root, "RSH-F-15", 10)
    digest = frozen_unchanged(root)
    held = inference_hash_holds(root)
    ok(f"sentence status: five rules, two judge questions, shared verify, typed prompts; {n} RSH-F-15 tests; audit files unchanged ({digest}); {held}")


def part_realcase(root: Path) -> None:
    out = root / "data" / "realcase"
    for name in ("items.jsonl", "meta.json", "test_sheet.md"):
        if not (out / name).exists():
            block(f"data/realcase/{name} not found (scripts/build_realcase_set.py)")
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    items = [json.loads(ln) for ln in (out / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    test = [it for it in items if it["split"] == "test"]
    if not 80 <= len(test) <= 100:
        block(f"the test split has {len(test)} items (SPEC: about 90)")
    if {it["paper"] for it in test} != {"P2", "P3"} or any(it["paper"] == "P1" for it in test):
        block("the test split must be P2 and P3 only (dev is P1)")
    labels_path = out / "labels_test.json"
    if not labels_path.exists():
        block("no labels yet: Chris labels data/realcase/test_sheet.md, then scripts/record_realcase_labels.py --by Chris")
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    who = labels.get("labelled_by", "")
    if not who or any(w in who.lower() for w in ("claude", "agent", "test", "evaluator")):
        block(f"the test split must be labelled by someone other than the checks' author, not {who!r}")
    if who != "Chris" and not labels.get("attribution_corrected"):
        block(f"labels by {who!r} differ from the SPEC (Chris labels); the labels file must say why")
    if labels["labelled_at"] <= meta["built_at"]:
        block("labels predate the set they label")
    if labels["sheet_sha256"] != meta["sheet_sha256"]:
        block("labels were recorded from a different sheet")
    missing = sorted({it["sheet_id"] for it in test} - set(labels["labels"]))
    if missing:
        block(f"no label for {missing}")
    bad = sum(1 for it in test if labels["labels"][it["sheet_id"]] in ("M", "X", "D", "O"))
    ok(f"real-case set: {len(test)} test items labelled by {who} at {labels['labelled_at']}; {bad} labelled faulty")


def part_audit(root: Path) -> None:
    module = root / "vera" / "audit" / "sentences.py"
    if not module.exists():
        block("vera/audit/sentences.py not found")
    text = module.read_text(encoding="utf-8")
    for needed in ("def from_text(", "def from_records(", "def audit(", "sentence_checks.within_quote", "sentence_checks.no_fact",
                   "sentence_checks.check_statement("):  # fmt: skip
        if needed not in text:
            block(f"the sentence audit lacks {needed}")
    pipeline = (root / "vera" / "app" / "pipeline.py").read_text(encoding="utf-8")
    if pipeline.count("_with_sentences(run,") < 2:
        block("both the review's and the paper's audit must run the sentence audit")
    pdf = (root / "vera" / "app" / "pdf.py").read_text(encoding="utf-8")
    for needed in ("SENTENCE_LIGHT_WORDS", "Synthesis sentences", "same_quote_as", "of this paper", "of this run"):
        if needed not in pdf:
            block(f"the PDF lacks {needed!r}")
    js = (root / "vera" / "app" / "static" / "app.js").read_text(encoding="utf-8")
    if "markSynthesis(" not in js or 'class: "synth"' not in js or "Spent on this run" not in js:
        block("the reader does not mark synthesis sentences or say which spend it shows")
    if '"sentences"' not in (root / "vera" / "app" / "server.py").read_text(encoding="utf-8"):
        block("the server does not send the sentences to the reader")
    for name in ("paper-light.png", "paper-dark.png", "paper-narrow.png"):
        png = root / "docs" / "screenshots" / name
        if not png.exists() or png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            block(f"docs/screenshots/{name} is missing or not a PNG")
    n = has_tests(root, "AUD-F-12", 6)
    digest = frozen_unchanged(root)
    held = inference_hash_holds(root)
    ok(f"sentence audit in both audits, reader and PDF; {n} AUD-F-12 tests; audit files unchanged ({digest}); {held}")


def part_measured(root: Path) -> None:
    sys.path.insert(0, str(root / "scripts"))
    import measure_realcase as mr  # noqa: PLC0415 - hashes computed exactly as the measurement computes them

    from vera.ledger import Ledger  # noqa: PLC0415

    freeze = root / "data" / "results" / "realcase_hash_incr7.json"
    result_path = root / "data" / "results" / "realcase_incr7_test.json"
    if not freeze.exists():
        block("no freeze (scripts/measure_realcase.py freeze)")
    if not result_path.exists():
        block("no test result (scripts/measure_realcase.py test)")
    frozen = json.loads(freeze.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if frozen["test_sha256"] != mr.test_hash() or frozen["check_sha256"] != mr.check_hashes():
        block("the test split, its labels or a check changed after the freeze")
    if result["run_at"] <= frozen["frozen_at"] or result["test_sha256"] != frozen["test_sha256"] or result["check_sha256"] != frozen["check_sha256"]:
        block("the test result does not come after the freeze, on the frozen set and checks")
    for t in ("claim", "sentence", "inference"):
        s = result["summary"].get(t) or {}
        for key in ("old_faulty_flagged", "new_faulty_flagged", "old_sound_flagged", "new_sound_flagged"):
            if "ci95" not in (s.get(key) or {}):
                block(f"the result lacks {t} {key} with its interval")
    spend = sum(sum(r.cost_usd for r in Ledger(p).records()) for p in (root / "data" / "ledger").glob("realcase_incr7_*.jsonl"))
    if spend > mr.CAP_USD:
        block(f"measurement spend ${spend:.4f} is over its ${mr.CAP_USD:.2f} cap")
    s = result["summary"]
    line = "; ".join(f"{t} faulty {s[t]['old_faulty_flagged']['k']}->{s[t]['new_faulty_flagged']['k']}/{s[t]['new_faulty_flagged']['n']}, "
                     f"sound {s[t]['old_sound_flagged']['k']}->{s[t]['new_sound_flagged']['k']}/{s[t]['new_sound_flagged']['n']}" for t in s)
    ok(f"measured after the freeze ({frozen['frozen_at']}): {line}; spend ${spend:.4f} of ${mr.CAP_USD:.2f}")


def part_coverage(root: Path) -> None:
    lit = root / "vera" / "literature"
    module = lit / "coverage.py"
    if not module.exists():
        block("vera/literature/coverage.py not found")
    text = module.read_text(encoding="utf-8")
    if "MAX_LOOKUPS = 3" not in text or "def named_targets(" not in text or "def threats_note(" not in text:
        block("the targeted search lacks the SPEC's limit (3 lookups), target reading or its threats note")
    stage = (lit / "paper_stage.py").read_text(encoding="utf-8")
    if stage.find("coverage.lookup(") < 0 or stage.find("coverage.lookup(") > stage.find("paper_evidence.widen("):
        block("the targeted search must run in the widening step, before the evidence is widened")
    if "coverage.threats_note(" not in stage:
        block("the threats section does not state what was searched for")
    if "added: list[dict]" not in (lit / "paper_evidence.py").read_text(encoding="utf-8"):
        block("widen() does not read the works the search found")
    if "added_records.jsonl" not in (root / "vera" / "app" / "server.py").read_text(encoding="utf-8"):
        block("the reader does not show sources the targeted search added")
    n = has_tests(root, "RSH-F-16", 4)
    digest = frozen_unchanged(root)
    held = inference_hash_holds(root)
    ok(f"targeted search: at most 3 lookups, before widening, threats note, reader sources; {n} RSH-F-16 tests; audit files unchanged ({digest}); {held}")


PARTS = {"sentences": part_sentences, "realcase": part_realcase, "audit": part_audit, "measured": part_measured,
         "coverage": part_coverage}  # fmt: skip


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--part", choices=sorted(PARTS), required=True)
    args = parser.parse_args()
    PARTS[args.part](args.root)


if __name__ == "__main__":
    main()

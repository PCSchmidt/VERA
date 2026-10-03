# Provenance of the rubric score files (2026-10-03)

Three files hold scores for the four topic outputs (A-lit, A-paper, B, C). They are kept as they were written; this note says
what each one is, so none is read as more than it is.

| File | Scorer | Blind to the others? | What it is |
|---|---|---|---|
| `rubric_evaluator.json` | a fresh subagent, told to read only the committed outputs | yes | the only independent scoring; unedited |
| `rubric_chris.json` | labelled "Chris" | **no** | **not Chris's own scoring.** All 20 scores equal `rubric_evaluator.json`; the four entries were written within one second by a script; Chris has said they should not be counted as independent evidence |
| `rubric_codex.json` | the Codex assistant, at Chris's request | **no** (it had already read `rubric_evaluator.json`) | a re-read of B and C only; scores equal the reviewer's; useful as a record that someone re-read them, not as a second opinion |

**Chris has not scored the outputs himself.** The SPEC's "Product bar" asks for his scores beside the independent
reviewer's; that requirement is unmet, and the Increment 3 review records it as a deviation. A-lit and A-paper have one
independent scoring (the subagent's); B and C have one independent scoring plus a non-blind re-read.

Anyone who scores the outputs blind later can append with `scripts/record_rubric.py`; entries are added, never replaced.

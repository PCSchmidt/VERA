"""The write-up stage (RSH-F-07): a crude, honest paper-shaped document, checked against the run's output guidance.

The model writes the prose. VERA writes what must not come from a model: the results table (rendered from the
harness's results, the same table the gates judged), `results.json`, and the reference list (from the records the
loop retrieved, `vera.loop.references`). The prose may cite only `[R1]`, `[R2]`, ...; a citation with no
retrieved record is a guidance failure here and a `fail` finding in the final audit.

Guidance checks. Deterministic: a word limit (`max_words`), required sections (a markdown heading each) and
`forbid: <phrase>` constraints. Anything else in `constraints` is plain language for the judge
(`loop.guidance_met`); the gate passes only if the deterministic checks pass *and* the judge confidently says the
guidance is met. A rejected write-up is regenerated once with the problems listed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from vera.loop import references, tables
from vera.loop.stages import LoopDeps, _stop, _write_json, ask_gate, finish, stage_result
from vera.schemas import OutputGuidance, Question, QuestionType

TABLE_TOKEN = "[[RESULTS_TABLE]]"
DEFAULT_SECTIONS = ["Abstract", "Method", "Results", "Limitations", "References"]
MAX_ATTEMPTS = 2
WRITE_SYSTEM = (
    "You write short, plain, honest research reports. You never invent results, citations or numbers: you use only "
    "the facts you are given."
)


# ── guidance checks ──────────────────────────────────────────────────────────────────────────────────


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def has_section(text: str, section: str) -> bool:
    pattern = rf"^\s*#{{1,6}}\s*(?:\d+\.?\s*)?{re.escape(section)}\b"
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def forbidden(guidance: OutputGuidance) -> list[str]:
    return [c.split(":", 1)[1].strip() for c in guidance.constraints if c.lower().startswith("forbid:")]


def free_text_constraints(guidance: OutputGuidance) -> list[str]:
    return [c for c in guidance.constraints if not c.lower().startswith("forbid:")]


def check_guidance(text: str, guidance: OutputGuidance, refs: list[dict]) -> list[str]:
    """Deterministic problems with `text`; empty means it passes the checks a program can make."""
    problems = []
    if guidance.max_words is not None and word_count(text) > guidance.max_words:
        problems.append(f"too long: {word_count(text)} words, the limit is {guidance.max_words}")
    for section in guidance.required_sections:
        if not has_section(text, section):
            problems.append(f"missing required section: {section}")
    lowered = text.lower()
    for phrase in forbidden(guidance):
        if phrase.lower() in lowered:
            problems.append(f"contains forbidden content: {phrase!r}")
    known = {r["key"] for r in refs}
    cited = set(re.findall(r"\[(R\d+)\]", text.split("## References")[0]))
    if cited - known:
        problems.append(f"cites records that were not retrieved: {sorted(cited - known)}")
    return problems


# ── generation ───────────────────────────────────────────────────────────────────────────────────────


def facts(state: dict, deps: LoopDeps) -> str:
    results = state["results"]
    ideas = {i["name"]: i["description"] for i in state["ideas"]}
    ran = [m for m in results if m != tables.BASELINE]
    best = state.get("best")
    lines = [
        f"- Baseline reproduced against the paper's reference values within the registered tolerance: yes "
        f"(gate verdict {state['verdicts']['baseline']['answer']}).",
        f"- Datasets: {', '.join(tables.dataset_label(d) for d in tables.valid_datasets(results, deps.datasets))}; "
        f"{deps.n_seeds} seeds; xgboost with 100 trees; held-out data; metric: Residual MSE (%), lower is better.",
        f"- Ideas generated: {len(state['ideas'])}; run on the subset: {len(ran)}.",
        "- Outcome: "
        + (f'"{best}" beat the baseline on every dataset.' if best else "no idea beat the baseline on every dataset."),
    ]
    shown = tables.valid_datasets(results, deps.datasets)
    if all("residual_in_sample_pct" in results[tables.BASELINE][d] for d in shown):  # absent in older results
        in_sample = "; ".join(
            f"{tables.dataset_label(d)} {tables.fmt_sig(results[tables.BASELINE][d]['residual_in_sample_pct']['mean'])}"
            for d in shown
        )
        lines.insert(
            1,
            f"- Baseline residual MSE (%), in-sample (the paper's convention): {in_sample}. "
            "The results table shows held-out values, which are higher.",
        )
    lines += [f"- {m}: {ideas.get(m, '')}" for m in ran]
    return "\n".join(lines)


def writeup_prompt(deps: LoopDeps, state: dict, refs: list[dict], problems: list[str] | None, previous: str | None):
    g = deps.spec.guidance
    sections = g.required_sections or DEFAULT_SECTIONS
    table = tables.render_results(state["results"], deps.datasets, deps.n_seeds)
    prompt = (
        "Write a short research report on an attempt to improve TreeHFD, a method that decomposes an xgboost model "
        "into main effects and second-order interactions. Facts you may use (nothing else):\n\n"
        f"{facts(state, deps)}\n\nResults table (do not retype it; put the exact token {TABLE_TOKEN} where it "
        f"belongs, in the Results section):\n\n{table}\n\n"
        "References you may cite, only as [R1], [R2], ... (the reference list is added for you; do not write one):\n"
        + "\n".join(references.format_reference(r) for r in refs)
        + "\n\nOutput guidance (follow every item):\n"
        f"- Format: {g.format}. Use markdown headings (## Section) for these sections, in this order: "
        f"{', '.join(sections)}.\n"
        + (f"- At most {g.max_words} words.\n" if g.max_words else "")
        + (f"- Emphasis: {g.emphasis}\n" if g.emphasis else "")
        + "".join(f"- {c}\n" for c in g.constraints)
        + "\nBe honest: say what the crude loop did and did not establish, state plainly if no idea beat the "
        "baseline, and describe the limits (few seeds, two datasets, one model configuration, ideas produced "
        "and implemented by a language model). Do not state any number that is not in the table or the facts."
    )
    if problems:
        prompt += f"\n\nYour previous draft was rejected: {'; '.join(problems)}.\nPrevious draft:\n{previous}\nFix it."
    return prompt


def assemble(text: str, state: dict, deps: LoopDeps, refs: list[dict]) -> str:
    """Put VERA's own table and reference list into the model's prose."""
    body = text.split("## References")[0].rstrip() if "## References" in text else text.rstrip()
    table = tables.render_results(state["results"], deps.datasets, deps.n_seeds)
    if TABLE_TOKEN in body:
        body = body.replace(TABLE_TOKEN, table)
    elif re.search(r"^\s*#{1,6}\s*(?:\d+\.?\s*)?Results\b.*$", body, re.IGNORECASE | re.MULTILINE):
        body = re.sub(
            r"(^\s*#{1,6}\s*(?:\d+\.?\s*)?Results\b.*$)",
            lambda m: f"{m.group(1)}\n\n{table}",
            body,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    else:
        body += f"\n\n{table}"
    return body + "\n\n## References\n\n" + "\n".join(references.format_reference(r) for r in refs) + "\n"


def results_json(state: dict, deps: LoopDeps) -> dict:
    """The run's numbers, as the harness reported them: what the audit matches the write-up against."""
    return {
        "run_id": deps.spec.run_id, "metric": "residual_mse_pct", "n_seeds": deps.n_seeds,
        "datasets": tables.valid_datasets(state["results"], deps.datasets), "results": state["results"],
        "best": state.get("best"), "ideas": state["ideas"],
    }  # fmt: skip


def write_up_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        refs = references.load_references(deps.run_dir)
        text, problems = None, None
        for _ in range(MAX_ATTEMPTS):
            prompt = writeup_prompt(deps, state, refs, problems, text)
            reply = deps.generator.generate(WRITE_SYSTEM, prompt, component="p3.write_up")
            text = assemble(reply, state, deps, refs)
            problems = check_guidance(text, deps.spec.guidance, refs)
            if not problems:
                break
        paper = deps.run_dir / "paper.md"
        paper.write_text(text, encoding="utf-8")
        rj = _write_json(deps, "results", results_json(state, deps))
        return {"artifacts": {"write_up_raw": "paper.md", "results_json": rj}, "trail": ["write_up"]}

    return node


GUIDANCE_QUESTION = Question(
    id="loop.guidance_met",
    type=QuestionType.BOOLEAN,
    text=(
        "Does the report follow every item of its output guidance (format, sections, length, emphasis and each "
        "constraint)? Answer false if any item is not met."
    ),
)


def writeup_gate_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        refs = references.load_references(deps.run_dir)
        text = (deps.run_dir / "paper.md").read_text(encoding="utf-8")
        g = deps.spec.guidance
        problems = check_guidance(text, g, refs)
        material = (
            "Output guidance:\n"
            f"- Format: {g.format}; sections: {', '.join(g.required_sections or DEFAULT_SECTIONS)}"
            + (f"; at most {g.max_words} words (the report has {word_count(text)})" if g.max_words else "")
            + (f"\n- Emphasis: {g.emphasis}" if g.emphasis else "")
            + "".join(f"\n- {c}" for c in g.constraints)
            + f"\n\nReport:\n\n{text}"
        )
        shadow = (not problems) if not free_text_constraints(g) else None
        verdict, confident = ask_gate(deps, "write_up", GUIDANCE_QUESTION, material, shadow, state)
        passed = not problems and confident and verdict.answer is True
        metrics = {"words": float(word_count(text)), "problems": float(len(problems))}
        reason = "; ".join(problems) if problems and not passed else None  # a deterministic cause, not a verdict
        deciding = [0] if not passed and not (confident and verdict.answer is True) else []
        sr = stage_result(deps, "write_up", "paper.md", verdict, "accept" if passed else "reject", metrics,
                          deciding, reason)
        update = {"verdicts": {"guidance_met": verdict.model_dump(mode="json")}, "stage_results": [sr],
                  "artifacts": {"write_up": "paper.md"}, "trail": ["writeup_gate"]}  # fmt: skip
        if not passed:
            why = "; ".join(problems) if problems else "the judge did not confirm the guidance was met"
            update |= _stop("write_up", f"gate: write-up rejected ({why})")
        (deps.run_dir / "artifacts" / "writeup_check.json").write_text(
            json.dumps({"problems": problems, "shadow": shadow}, indent=1), encoding="utf-8"
        )
        return finish(update)

    return node

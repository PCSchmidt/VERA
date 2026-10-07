# ruff: noqa: E501
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

from vera.loop import ablation, figures, literature_context, problem, references, tables
from vera.loop.stages import LoopDeps, _stop, _write_json, ask_gate, extension_datasets, finish, stage_result
from vera.schemas import OutputGuidance, Question, QuestionType

TABLE_TOKEN = "[[RESULTS_TABLE]]"
PROTOCOL_TOKEN = "[[PROTOCOL_TABLES]]"
FIGURE_TOKEN = "[[FIGURE:{}]]"
DEFAULT_SECTIONS = ["Abstract", "Method", "Results", "Limitations", "References"]
MAX_ATTEMPTS = 2
WRITE_SYSTEM = (
    "You write short, plain, honest research reports. You never invent results, citations or numbers: you use only "
    "the facts you are given."
)


# ── guidance checks ──────────────────────────────────────────────────────────────────────────────────


def prose_word_count(text: str) -> int:
    """Words of the report's prose: what the length limit counts. VERA's own tables (their rows and bold titles) and
    the reference list are not the writer's words."""
    body = text.split("## References")[0]
    prose = [ln for ln in body.splitlines() if not ln.lstrip().startswith(("|", "**"))]
    return word_count("\n".join(prose))


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def has_section(text: str, section: str) -> bool:
    pattern = rf"^\s*#{{1,6}}\s*(?:\d+\.?\s*)?{re.escape(section)}\b"
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def forbidden(guidance: OutputGuidance) -> list[str]:
    return [c.split(":", 1)[1].strip() for c in guidance.constraints if c.lower().startswith("forbid:")]


def free_text_constraints(guidance: OutputGuidance) -> list[str]:
    return [c for c in guidance.constraints if not c.lower().startswith("forbid:")]


def check_guidance(text: str, guidance: OutputGuidance, refs: list[dict], figs: list[dict] | None = None) -> list[str]:
    """Deterministic problems with `text`; empty means it passes the checks a program can make."""
    problems = []
    if guidance.max_words is not None and prose_word_count(text) > guidance.max_words:
        problems.append(f"too long: {prose_word_count(text)} words, the limit is {guidance.max_words}")
    for section in guidance.required_sections:
        if not has_section(text, section):
            problems.append(f"missing required section: {section}")
    lowered = text.lower()
    for phrase in forbidden(guidance):
        if phrase.lower() in lowered:
            problems.append(f"contains forbidden content: {phrase!r}")
    for n, fig in enumerate(figs or [], start=1):  # every figure is in the report and referred to in its prose
        if f"figures/{fig['file']}" not in text:
            problems.append(f"figure {n} ({fig['id']}) is missing from the report")
        caption = re.compile(r"\s*Figure \d+\.")
        prose = "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith(("!", "|")) and not caption.match(ln)
        )
        if not re.search(rf"\bFigure {n}\b", prose):
            problems.append(f"Figure {n} is not referred to in the text")
    known = {r["key"] for r in refs}
    cited = set(re.findall(r"\[(R\d+)\]", text.split("## References")[0]))
    if cited - known:
        problems.append(f"cites records that were not retrieved: {sorted(cited - known)}")
    return problems


# ── generation ───────────────────────────────────────────────────────────────────────────────────────


def facts(state: dict, deps: LoopDeps) -> str:
    kit_facts = problem.active().extra.get("facts")
    if kit_facts:
        text = kit_facts(state, deps)
        extra = [*ablation.facts(state), *(protocol_facts(state["protocol"]) if state.get("protocol") else [])]
        return text + ("\n" + "\n".join(extra) if extra else "")
    results = state["results"]
    ideas = {i["name"]: i["description"] for i in state["ideas"]}
    ran = [m for m in results if m != tables.BASELINE and " without " not in m]  # ablation rows are not ideas
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
        registered = {d: deps.target.get("datasets", {}).get(d, {}).get("reproduction_metric") for d in shown}
        parts = []
        for d in shown:
            basis_in_sample = registered[d] == "residual_in_sample_pct"
            key = "residual_in_sample_pct" if basis_in_sample else "residual_mse_pct"
            parts.append(f"{tables.dataset_label(d)} {'in-sample' if basis_in_sample else 'held-out'} "
                         f"{tables.fmt_sig(results[tables.BASELINE][d][key]['mean'])}")  # fmt: skip
        lines.insert(
            1,
            "- The baseline was reproduced on the row set the registered target names for each dataset (the paper's own "
            f"convention for that dataset), with these baseline values (residual MSE, %): {'; '.join(parts)}. "
            "The results table shows held-out values for every dataset, which are higher than in-sample ones.",
        )
    lines += [
        f"- Dataset {tables.dataset_label(d)}: {text}" for d, text in extension_datasets(deps).items() if d in shown
    ]
    lines += [f"- {m}: {ideas.get(m, '')}" for m in ran if " without " not in m]
    lines += ablation.facts(state)
    if state.get("protocol"):
        lines += protocol_facts(state["protocol"])
    return "\n".join(lines)


def protocol_facts(protocol: dict) -> list[str]:
    """What the registered protocol measured, in words a model may use: the design, not the numbers (those are in
    the tables VERA renders)."""
    invalid = sum(not cell.get("valid") for cells in protocol["results"].values() for cell in cells.values())
    return [*trend_facts(protocol), *protocol_design_facts(protocol, invalid)]


def trend_facts(protocol: dict) -> list[str]:
    """What the parent's own method's rows show as the correlation rises (the Increment 3 paper did not remark on it)."""
    rows = sorted((float(d.split("@")[1]), d) for d in protocol["datasets"] if d.startswith("analytical@"))
    parent = protocol["methods"][0]
    out = []
    for key, name in (
        ("residual_mse_pct", "residual MSE (%)"),
        ("component_mse_pct", "component error (% of signal variance)"),
    ):
        pts = [
            (r, protocol["results"][parent][d].get(key)) for r, d in rows if protocol["results"][parent][d].get("valid")
        ]
        pts = [(r, v["mean"]) for r, v in pts if v]
        if len(pts) >= 2:
            (r0, v0), (r1, v1) = pts[0], pts[-1]
            out.append(f"- Trend in {parent}'s own {name}: {tables.fmt_sig(v0)} at correlation {r0:g} and {tables.fmt_sig(v1)} at {r1:g}; "
                       "the paper should remark on it.")  # fmt: skip
    return out


def protocol_design_facts(protocol: dict, invalid: int) -> list[str]:
    return [
        "- A registered protocol was run (written down, dated and hashed before any run): methods "
        + ", ".join(protocol["methods"])
        + "; datasets "
        + ", ".join(tables.protocol_dataset_label(d) for d in protocol["datasets"])
        + f"; {protocol['n_seeds']} seeds and {protocol['n_boot']} bootstrap refits of the ensemble per seed.",
        "- Component error compares each method's components with the TRUE decomposition of the analytical function, "
        "which has a closed form checked against the TreeHFD paper's Table 3; Airfoil has no true components. "
        "Rank stability is the mean Spearman correlation of component importances between bootstrap refits. "
        "TreeSHAP here is xgboost's path-dependent TreeSHAP with interaction values.",
        f"- Cells the harness could not compute: {invalid} (marked invalid in the tables).",
    ]


def writeup_prompt(
    deps: LoopDeps,
    state: dict,
    refs: list[dict],
    problems: list[str] | None,
    previous: str | None,
    figs: list[dict] | None = None,
):
    g = deps.spec.guidance
    sections = g.required_sections or DEFAULT_SECTIONS
    table = tables.render_results(state["results"], deps.datasets, deps.n_seeds)
    prompt = (
        (
            problem.active().writeup_intro
            or "Write a short research report on an attempt to improve TreeHFD, a method that decomposes an xgboost "
            "model into main effects and second-order interactions. "
        )
        + "Facts you may use (nothing else):\n\n"
        f"{facts(state, deps)}\n\nResults table (do not retype it; put the exact token {TABLE_TOKEN} where it "
        f"belongs, in the Results section):\n\n{table}\n\n"
        + (
            "Protocol results (do not retype; put the exact token "
            f"{PROTOCOL_TOKEN} in the Results section, after the table above):\n\n"
            + tables.render_protocol(state["protocol"])
            + "\n\n"
            if state.get("protocol")
            else ""
        )
        + figure_instructions(figs)
        + "References you may cite, only as [R1], [R2], ... (the reference list is added for you; do not write one):\n"
        + "\n".join(references.format_reference(r) for r in refs)
        + "\n\nOutput guidance (follow every item):\n"
        f"- Format: {g.format}. Use markdown headings (## Section) for these sections, in this order: "
        f"{', '.join(sections)}.\n"
        + (f"- At most {g.max_words} words, not counting tables or the reference list.\n" if g.max_words else "")
        + (f"- Emphasis: {g.emphasis}\n" if g.emphasis else "")
        + "".join(f"- {c}\n" for c in g.constraints)
        + "\nBe honest: say what the crude loop did and did not establish, state plainly if no idea beat the "
        "baseline, and describe the limits "
        + (
            problem.active().writeup_limits
            or "(few seeds, two datasets, one model configuration, ideas produced and implemented by a language model)"
        )
        + ". Do not state any number that is not in the table or the facts."
        + (literature_context.for_write_up(deps.extra["literature"]) if deps.extra.get("literature") else "")
    )
    if problems:
        prompt += f"\n\nYour previous draft was rejected: {'; '.join(problems)}.\nPrevious draft:\n{previous}\nFix it."
    return prompt


def assemble(text: str, state: dict, deps: LoopDeps, refs: list[dict], figs: list[dict] | None = None) -> str:
    """Put VERA's own table and reference list into the model's prose."""
    body = text.split("## References")[0].rstrip() if "## References" in text else text.rstrip()
    table = tables.render_results(state["results"], deps.datasets, deps.n_seeds)
    body = place_figures(body, figs or [])
    if state.get("protocol"):
        protocol_tables = tables.render_protocol(state["protocol"])
        if PROTOCOL_TOKEN in body:
            body = body.replace(PROTOCOL_TOKEN, protocol_tables)
        else:  # the model left the token out: the tables go straight after the main table's section start
            body += f"\n\n{protocol_tables}"
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


def figure_instructions(figs: list[dict] | None) -> str:
    """The part of the prompt about figures VERA drew: where to put each, and what the model writes (the captions)."""
    if not figs:
        return ""
    lines = [
        f"Figure {n}: {f['title']} (put the exact token {FIGURE_TOKEN.format(f['id'])} on its own line in the Results "
        f"section, then one caption sentence starting 'Figure {n}.')"
        for n, f in enumerate(figs, start=1)
    ]
    return (
        "Figures (drawn for you from the results; do not describe values you cannot read from the tables; write only "
        "each caption and refer to every figure in the text as 'Figure N'):\n" + "\n".join(lines) + "\n\n"
    )


def place_figures(body: str, figs: list[dict]) -> str:
    """Replace each figure token by the image VERA drew; a figure the model left out is appended with a plain caption
    and a sentence that refers to it."""
    for n, f in enumerate(figs, start=1):
        image = f"![Figure {n}](figures/{f['file']})"
        token = FIGURE_TOKEN.format(f["id"])
        if token in body:
            body = body.replace(token, image)
        elif f"figures/{f['file']}" not in body:
            body += f"\n\n{image}\n\nFigure {n}. {f['title']}, drawn from results.json."
            body += f"\n\nFigure {n} shows the same numbers as the tables, drawn from results.json."
    return body


def results_json(state: dict, deps: LoopDeps) -> dict:
    """The run's numbers, as the harness reported them: what the audit matches the write-up against."""
    return {
        "run_id": deps.spec.run_id, "metric": tables.PRIMARY, "n_seeds": deps.n_seeds,
        "metrics": [list(m) for m in tables.METRICS], "baseline_label": tables.BASELINE,
        "datasets": tables.valid_datasets(state["results"], deps.datasets), "results": state["results"],
        "best": state.get("best"), "ideas": state["ideas"],
        **({"protocol": state["protocol"]} if state.get("protocol") else {}),
    }  # fmt: skip


def write_up_node(deps: LoopDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        refs = references.load_references(deps.run_dir)
        rj_now = results_json(state, deps)
        figs = figures.draw(rj_now, figures.plan(rj_now), deps.run_dir / "figures")
        text, problems = None, None
        for _ in range(MAX_ATTEMPTS):
            prompt = writeup_prompt(deps, state, refs, problems, text, figs)
            reply = deps.generator.generate(WRITE_SYSTEM, prompt, component="p3.write_up")
            text = assemble(reply, state, deps, refs, figs)
            problems = check_guidance(text, deps.spec.guidance, refs, figs)
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
        fig_file = deps.run_dir / "figures" / "figures.json"
        figs = json.loads(fig_file.read_text(encoding="utf-8")) if fig_file.exists() else []
        problems = check_guidance(text, g, refs, figs)
        material = (
            "Output guidance:\n"
            f"- Format: {g.format}; sections: {', '.join(g.required_sections or DEFAULT_SECTIONS)}"
            + (f"; at most {g.max_words} words (its prose has {prose_word_count(text)})" if g.max_words else "")
            + (f"\n- Emphasis: {g.emphasis}" if g.emphasis else "")
            + "".join(f"\n- {c}" for c in g.constraints)
            + f"\n\nReport:\n\n{text}"
        )
        shadow = (not problems) if not free_text_constraints(g) else None
        verdict, confident = ask_gate(deps, "write_up", GUIDANCE_QUESTION, material, shadow, state)
        passed = not problems and confident and verdict.answer is True
        metrics = {"words": float(prose_word_count(text)), "problems": float(len(problems))}
        reason = "; ".join(problems) if problems and not passed else None  # a deterministic cause, not a verdict
        deciding = [0] if not passed and not (confident and verdict.answer is True) else []
        sr = stage_result(
            deps, "write_up", "paper.md", verdict, "accept" if passed else "reject", metrics, deciding, reason
        )
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

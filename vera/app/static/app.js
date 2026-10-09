"use strict";
/* VERA local app. No external scripts; every figure on a page comes from /api/facts or a run's own files. */

const $ = (sel, root = document) => root.querySelector(sel);
const main = $("#main");
const forced = new URLSearchParams(location.search).get("theme");
if (forced === "dark" || forced === "light") document.documentElement.dataset.theme = forced;
const state = { config: null, facts: null };

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) node.append(kid instanceof Node ? kid : document.createTextNode(String(kid ?? "")));
  return node;
}
const money = (n) => (n < 0.1 ? "$" + n.toFixed(3) : "$" + n.toFixed(2));
const when = (s) => (s ? new Date(s).toLocaleString() : "");

async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: {} };
  if (opts.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, init);
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(typeof d === "string" ? d : "Something went wrong (" + res.status + ").");
  }
  return data;
}

async function loadBasics() {
  [state.config, state.facts] = await Promise.all([api("/api/config"), api("/api/facts")]);
  paintKey();
}

function paintKey() {
  const c = state.config;
  const ok = c && c.key_source !== "none";
  $("#keypill").className = "keystate" + (ok ? " ok" : "");
  $("#keytext").textContent = !c ? "Checking key…" : c.key_source === "session" ? "Key connected (this session)"
    : c.key_source === "env" ? "Key found in your environment" : "Connect your key";
}

/* ── routing ───────────────────────────────────────────────────────────── */

const routes = [
  [/^#\/?$/, landing],
  [/^#\/new$/, newRun],
  [/^#\/runs$/, runsList],
  [/^#\/run\/([a-z0-9-]+)$/, runView],
  [/^#\/read\/([a-z0-9-]+)$/, (id) => readerView("run", id)],
  [/^#\/examples$/, examplesView],
  [/^#\/example\/([a-z0-9-]+)$/, (id) => readerView("example", id)],
];
let closeStream = null;

async function route() {
  if (closeStream) { closeStream(); closeStream = null; }
  const hash = location.hash || "#/";
  for (const link of document.querySelectorAll("nav a")) link.removeAttribute("aria-current");
  const nav = hash.startsWith("#/new") ? "new" : hash.startsWith("#/run") || hash.startsWith("#/read") ? "runs" : hash.startsWith("#/example") ? "examples" : null;
  if (nav) $(`nav a[data-nav="${nav}"]`).setAttribute("aria-current", "page");
  for (const [re, view] of routes) {
    const m = hash.match(re);
    if (m) {
      main.replaceChildren(el("p", { class: "hint" }, "Loading…"));
      try { main.replaceChildren(...[await view(...m.slice(1))].flat()); } catch (e) { main.replaceChildren(el("p", { class: "error", role: "alert" }, e.message)); }
      main.focus();
      window.scrollTo(0, 0);
      return;
    }
  }
  location.hash = "#/";
}
window.addEventListener("hashchange", route);

/* ── landing ───────────────────────────────────────────────────────────── */

function costRange(r) {
  if (!r) return "an amount shown after your first run";
  return r.low === r.high ? money(r.low) : money(r.low) + " and " + money(r.high);
}

async function landing() {
  const f = state.facts, c = state.config, s = f.review_scores;
  const check = (yes, ok, no) => el("li", { class: yes ? "yes" : "" }, yes ? ok : no);
  const first = f.examples[0];
  return [
    el("section", { class: "hero" },
      el("p", { class: "kicker" }, "Research assistant, on your own key"),
      el("h1", {}, "Literature reviews you can check."),
      el("p", { class: "lede" }, "Give VERA a topic. It proposes one research question for you to confirm, searches and reads the literature, writes a review in which every claim is tied to a quote, and audits the result. You see the audit, not just the answer."),
      el("div", { class: "row" },
        el("a", { class: "button primary", href: "#/new" }, "Start a run"),
        el("a", { class: "button", href: first ? "#/example/" + first.id : "#/examples" }, "Read a finished example"))),
    el("section", {},
      el("h2", {}, "How it works"),
      el("ol", { class: "steps" },
        el("li", {}, el("h3", {}, "Propose"), el("p", {}, "Your topic becomes one researchable question. You confirm it or edit it before anything more is spent.")),
        el("li", {}, el("h3", {}, "Search and read"), el("p", {}, "Several paper-search services are queried; the most relevant papers are read, in full text where possible.")),
        el("li", {}, el("h3", {}, "Write with quotes"), el("p", {}, "Every claim in the review is tied to an exact quote from a source. A claim that cannot be quoted is removed.")),
        el("li", {}, el("h3", {}, "Audit"), el("p", {}, "Citations are checked to exist and each claim to be supported by its quote. The result is shown in plain words.")))),
    el("div", { class: "callout" },
      el("h2", {}, "Whose key and whose money"),
      el("p", {}, "Yours. VERA runs on the model key you connect, and every model call is charged to your account. The maintainer pays nothing and has no access to your key or your runs. The key stays in this program's memory; it is never written to a file or a log."),
      el("p", {}, "You set a spending cap on every run. VERA stops before it would pass the cap and keeps what it has done so far."),
      el("div", { class: "row" }, el("button", { type: "button", onclick: openKeyDialog }, "Connect my key"))),
    el("section", { class: "facts" },
      el("div", { class: "fact" }, el("h3", {}, "What a run costs"),
        el("p", {}, "In our own example runs, a literature review cost between " + costRange(f.literature_cost_usd) + " in model fees, and a run that also ran experiments cost between " + costRange(f.paper_cost_usd) + ". Your cost depends on the topic and the model; the cap you set is the limit."),
        el("p", { class: "hint" }, "Figures are read from the example runs' own ledgers.")),
      el("div", { class: "fact" }, el("h3", {}, "What to expect"),
        el("p", {}, "These are working drafts, not finished papers. In the maintainer's own blind scoring of " + s.n_reviews + " reviews, the strongest criterion was " + s.strongest + " (average " + s.strongest_mean + " out of " + s.scale + ") and the weakest was " + s.weakest + " (average " + s.weakest_mean + " out of " + s.scale + "). VERA's search misses papers, and the review says so."),
        el("p", { class: "hint" }, "A run can end without a better method than the one it started from. That is a normal result, and it is reported as one.")),
      el("div", { class: "fact" }, el("h3", {}, "What it will not do"),
        el("p", {}, "It will not produce wet-lab science, use data you do not have the right to use, or run experiments that need more than a laptop. A green audit means the citations are real and each claim is supported by the passage it quotes. It does not mean the review is complete or the conclusions are right."))),
    el("section", {},
      el("h2", {}, "Before you start"),
      el("ul", { class: "checks" },
        check(c.key_source !== "none", "A model key is connected.", "No model key yet. Connect your own to start."),
        check(c.docker_available, "Docker was found (needed only for experiments).", "Docker was not found. Literature reviews work without it; experiments need it."),
        check(c.grobid_available, "The full-text reader (GROBID) is running.", "The full-text reader (GROBID) is not running. VERA then reads abstracts only and says so in the review."),
        check(c.semantic_scholar_key || c.openalex_key, "An extra paper-search key was found, so more sources are searched.", "No extra paper-search key. Two free sources are searched; adding your own Semantic Scholar or OpenAlex key widens the search."))),
  ];
}

/* ── key dialog ────────────────────────────────────────────────────────── */

const dialog = $("#keydialog");
function openKeyDialog() { $("#keyerror").hidden = true; $("#keyinput").value = ""; dialog.showModal(); $("#keyinput").focus(); }
$("#keypill").addEventListener("click", openKeyDialog);
$("#keyclose").addEventListener("click", () => dialog.close());
$("#keyforget").addEventListener("click", async () => {
  await api("/api/key", { method: "DELETE" });
  state.config = await api("/api/config");
  paintKey();
  dialog.close();
});
$("#keyform").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const err = $("#keyerror");
  err.hidden = true;
  try {
    await api("/api/key", { method: "POST", body: { key: $("#keyinput").value } });
    $("#keyinput").value = "";
    state.config = await api("/api/config");
    paintKey();
    dialog.close();
    route();
  } catch (e) { err.textContent = e.message; err.hidden = false; }
});

/* ── new run ───────────────────────────────────────────────────────────── */

function slug(text) {
  const words = text.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().split(" ").filter(Boolean);
  let base = "";
  for (const w of words) { if ((base + "-" + w).length > 34) break; base += (base ? "-" : "") + w; }
  return (base || "run") + "-" + Math.random().toString(36).slice(2, 6);
}

const LENGTHS = [["Short (about a page)", 1000], ["Standard", 1500], ["Detailed (a few pages)", 2500]];

async function newRun() {
  const err = el("p", { class: "error", role: "alert", hidden: true });
  const topic = el("textarea", { id: "topic", required: true, placeholder: "For example: how well do conformal prediction methods keep their guarantees when the data distribution shifts?" });
  const emphasis = el("textarea", { id: "emphasis", placeholder: "What to emphasise, what to avoid, who it is for." });
  const length = el("select", { id: "length" }, ...LENGTHS.map(([label, words], i) => el("option", { value: words, selected: i === 1 }, label)));
  const cap = el("input", { id: "cap", type: "number", min: "0.1", max: "25", step: "0.1", value: "1", required: true });
  const form = el("form", {},
    el("p", { class: "kicker" }, "New run"),
    el("h1", {}, "What would you like reviewed?"),
    el("p", { class: "lede" }, "Describe the topic in a sentence or two. VERA will propose one question from it and wait for you to confirm or edit it before spending more."),
    el("label", { for: "topic" }, "Topic"),
    topic,
    el("p", { class: "hint field-note" }, "If your topic uses acronyms or new terms, define them here. The proposal is only as good as the topic you give it."),
    el("label", { for: "length" }, "Length of the review"),
    length,
    el("label", { for: "cap" }, "Spending cap (US dollars)"),
    cap,
    el("p", { class: "hint field-note" }, "VERA stops before it would pass this. A literature review typically costs a fraction of it."),
    el("details", {}, el("summary", {}, "More guidance for the write-up (optional)"), emphasis),
    el("p", { class: "hint" }, "This version writes literature reviews. Running experiments is not available from this form; it works from the command line (see the README)."),
    err,
    el("div", { class: "row" }, el("button", { class: "primary", type: "submit" }, "Propose a question")));
  form.style.maxWidth = "40rem";
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    err.hidden = true;
    try {
      const body = {
        run_id: slug(topic.value), topic: topic.value, max_usd: parseFloat(cap.value), max_wall_seconds: 7200,
        allow_experiments: false, guidance: { format: "paper", max_words: parseInt(length.value, 10), emphasis: emphasis.value.trim() || null },
      };
      const st = await api("/api/runs", { method: "POST", body });
      location.hash = "#/run/" + st.run_id;
    } catch (e) { err.textContent = e.message; err.hidden = false; }
  });
  return [form];
}

/* ── runs ──────────────────────────────────────────────────────────────── */

const STATE_WORDS = {
  queued: "Starting", scoping: "Proposing a question", awaiting_confirmation: "Waiting for you to confirm the question",
  running: "Working", stopping: "Stopping", stopped: "Stopped", complete: "Finished", failed: "Could not continue",
};

function lightBadge(audit) {
  const words = { green: "Green: citations real, claims supported", amber: "Amber: read the warnings", red: "Red: failed checks" };
  return el("span", { class: "light " + (audit || "none"), title: audit ? words[audit] : "Not audited" }, audit ? audit + " audit" : "Not audited");
}

function shortTitle(t) {
  const first = t.split(/(?<=[.?!])\s/)[0];
  const base = first.length <= 120 ? first : first.slice(0, 117).replace(/\s+\S*$/, "") + "…";
  return base.replace(/[.]$/, "");
}

async function titleOf(id) {
  try { const r = await api("/api/runs/" + id + "/files/app_request.json"); return r.topic; } catch (_) { return id; }
}

async function runsList() {
  const runs = await api("/api/runs");
  const head = [el("p", { class: "kicker" }, "My runs"), el("h1", {}, "Your runs")];
  if (!runs.length) return [...head, el("p", { class: "lede" }, "No runs yet."), el("a", { class: "button primary", href: "#/new" }, "Start one")];
  const titles = await Promise.all(runs.map((r) => titleOf(r.run_id)));
  return [...head, el("ul", { class: "runlist" }, ...runs.map((r, i) => el("li", {},
    el("a", { class: "rl-title", href: "#/run/" + r.run_id }, shortTitle(titles[i])),
    el("div", { class: "rl-meta" }, el("span", { class: "tag" }, STATE_WORDS[r.state] || r.state), " ", lightBadge(r.audit), " ",
      "Spent " + money(r.spent_usd) + " of " + money(r.max_usd) + " · " + when(r.updated_at) + " · ", el("code", {}, r.run_id)))))];
}

const STAGES = [
  ["scope", "Question", "Turning your topic into one researchable question."],
  ["retrieve", "Search", "Querying the paper-search services and screening what they return."],
  ["read", "Read", "Reading the most relevant papers, in full text where possible."],
  ["synthesize", "Write", "Drafting the review and checking every claim against its quote."],
  ["parent", "Look for a parent problem", "Checking whether a published method with public code fits the question."],
];

function paintRun(box, r, title, topic) {
  const doneIdx = STAGES.findIndex((s) => s[0] === r.stage);
  const live = ["queued", "scoping", "running", "stopping"].includes(r.state);
  const finished = r.state === "complete";
  const pct = Math.min(100, (r.spent_usd / r.max_usd) * 100);
  const bar = el("div", { class: "meter-bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(r.max_usd), "aria-valuenow": String(r.spent_usd), "aria-label": "Spend against your cap" }, el("span"));
  bar.firstChild.style.width = pct.toFixed(1) + "%";
  const timeline = el("ol", { class: "timeline", "aria-label": "Stages" }, ...STAGES.map(([id, label, what], i) =>
    el("li", { class: finished || i <= doneIdx ? "done" : i === doneIdx + 1 && live ? "now" : "" }, el("span", { class: "t-name" }, label), el("span", { class: "t-what" }, what))));
  const nodes = [
    el("div", { class: "runhead" },
      el("p", { class: "kicker" }, "Run"),
      el("h1", {}, title),
      topic && topic !== title ? el("p", { class: "small topic" }, topic) : "",
      el("p", {}, el("span", { class: "tag" + (live ? " live" : "") }, STATE_WORDS[r.state] || r.state), " ", lightBadge(r.audit))),
    timeline,
    el("div", { class: "meter" }, bar, el("div", { class: "meter-text" }, el("span", {}, "Spent " + money(r.spent_usd)), el("span", {}, "Your cap " + money(r.max_usd)))),
  ];
  if (r.message) nodes.push(el("p", {}, r.message));
  if (r.last_verdict && r.last_verdict.question) nodes.push(el("p", { class: "small" }, "Latest check: " + r.last_verdict.question + " → " + r.last_verdict.answer + " (confidence " + (r.last_verdict.confidence ?? "n/a") + ", " + (r.last_verdict.backend || "") + ")"));
  const actions = el("div", { class: "row" });
  if (live && r.state !== "stopping") actions.append(el("button", { type: "button", onclick: () => act(r.run_id, "stop") }, "Stop"));
  if (["stopped", "failed"].includes(r.state)) actions.append(el("button", { type: "button", class: "primary", onclick: () => act(r.run_id, "resume") }, "Resume"));
  if (finished) actions.append(el("a", { class: "button primary", href: "#/read/" + r.run_id }, "Read the review"), el("a", { class: "button", href: "/api/runs/" + r.run_id + "/pdf" }, "Download PDF"));
  nodes.push(actions);
  box.replaceChildren(...nodes);
}

async function act(id, what, body) {
  try { await api("/api/runs/" + id + "/" + what, { method: "POST", body: body || {} }); } catch (e) { alert(e.message); }
}

async function runView(id) {
  const box = el("div");
  const scopeBox = el("div");
  const [st0, topic] = await Promise.all([api("/api/runs/" + id), titleOf(id)]);
  const title = shortTitle(topic);
  paintRun(box, st0, title, topic);
  let lastState = null;
  const es = new EventSource("/api/runs/" + id + "/events");
  closeStream = () => es.close();
  es.onmessage = async (ev) => {
    const r = JSON.parse(ev.data);
    paintRun(box, r, title, topic);
    if (r.state === "awaiting_confirmation" && lastState !== r.state) await paintScope(scopeBox, id);
    else if (r.state !== "awaiting_confirmation") scopeBox.replaceChildren();
    lastState = r.state;
  };
  es.onerror = () => { /* the stream ends at a stopping point; reload to watch again */ };
  return [box, scopeBox];
}

async function paintScope(box, id) {
  const sc = await api("/api/runs/" + id + "/scope");
  const q = el("textarea", { id: "q", "aria-label": "The question" });
  q.value = sc.question;
  box.replaceChildren(el("div", { class: "callout" },
    el("h2", {}, "Check the question before VERA spends more"),
    el("p", {}, "This is the question VERA will research. Edit it if it is not the one you meant."),
    q,
    el("p", { class: "hint" }, sc.why_researchable || ""),
    el("div", { class: "row" },
      el("button", { class: "primary", type: "button", onclick: () => act(id, "confirm", { question: q.value.trim() === sc.question ? null : q.value.trim() }) }, "Confirm and continue"))));
}

/* ── examples ──────────────────────────────────────────────────────────── */

async function examplesView() {
  return [
    el("p", { class: "kicker" }, "Examples"),
    el("h1", {}, "Finished examples"),
    el("p", { class: "lede" }, "Each example shows the exact inputs that produced it, what it cost, and the audit result. Two are literature reviews and two also ran experiments. Neither experiment found a better method than the baseline, and the papers say so."),
    ...state.facts.examples.map((e) => el("section", { class: "example" },
      el("div", {},
        el("p", { class: "kicker" }, e.kind === "paper" ? "With experiments" : "Literature review"),
        el("h2", {}, e.title),
        el("p", {}, lightBadge(e.audit), " ", el("span", { class: "small" }, "Spent " + money(e.spent_usd))),
        el("p", { class: "small" }, e.outcome),
        el("div", { class: "row" },
          el("a", { class: "button primary", href: "#/example/" + e.id }, "Read it with its evidence"),
          el("a", { class: "button", href: "/api/examples/" + e.id + "/pdf" }, "Download PDF"))),
      el("dl", { class: "inputs" },
        el("h3", { class: "kicker" }, "What went in"),
        el("dt", {}, "Topic"), el("dd", {}, e.topic),
        el("dt", {}, "Confirmed question"), el("dd", {}, e.question),
        el("dt", {}, "Guidance"), el("dd", {}, e.guidance.format + (e.guidance.max_words ? ", up to " + e.guidance.max_words + " words" : "") + (e.guidance.emphasis ? ". " + e.guidance.emphasis : "")),
        el("dt", {}, "Spending cap"), el("dd", {}, money(e.budget_cap_usd)))))
  ];
}

/* ── reader ────────────────────────────────────────────────────────────── */

function renderInline(text, ctx) {
  // **bold**, *italic*, `code`, [R12] citations, ![alt](src) images, [text](url) links; all text is inserted as text.
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\((?:https?:\/\/|#)[^)]+\)|\[R\d+\]|\u0001\d+\u0002[\s\S]*?\u0003)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) out.push(el("strong", {}, t.slice(2, -2)));
    else if (t.startsWith("`")) out.push(el("code", {}, t.slice(1, -1)));
    else if (t.startsWith("![")) {
      const [, alt, src] = t.match(/!\[([^\]]*)\]\(([^)]+)\)/);
      if (ctx.fileBase && !/^(https?:|\/)/.test(src)) out.push(el("img", { alt, src: ctx.fileBase + src }));
    } else if (t.startsWith("[R")) {
      const key = t.slice(1, -1);
      out.push(el("sup", { class: "cite", tabindex: "0", role: "button", onclick: () => showSource(ctx, key), onkeydown: (e) => { if (e.key === "Enter") showSource(ctx, key); } }, key));
    } else if (t.startsWith("[")) {
      const [, label, href] = t.match(/\[([^\]]+)\]\(([^)]+)\)/);
      out.push(el("a", { href, rel: "noopener noreferrer", target: "_blank" }, label));
    } else if (t.startsWith("\u0001")) {
      const i = parseInt(t.slice(1, t.indexOf("\u0002")), 10);
      const inner = t.slice(t.indexOf("\u0002") + 1, -1);
      out.push(el("span", { class: "claim", tabindex: "0", role: "button", onclick: () => showClaim(ctx, i), onkeydown: (e) => { if (e.key === "Enter") showClaim(ctx, i); } }, ...renderInline(inner, ctx)));
    } else out.push(el("em", {}, t.slice(1, -1)));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const REF = /^\[R\d+\]\s/;

function renderMarkdown(md, ctx) {
  const out = [];
  const lines = md.split("\n");
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) { out.push(el("h" + Math.min(h[1].length + 1, 4), {}, ...renderInline(h[2], ctx))); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(line)) {
      const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(lines[i]); i++; }
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const head = cells(rows[0]);
      const body = rows.slice(/^[\s|:-]+$/.test(rows[1] || "") ? 2 : 1).map(cells);
      out.push(el("table", {}, el("thead", {}, el("tr", {}, ...head.map((c) => el("th", {}, ...renderInline(c, ctx))))),
        el("tbody", {}, ...body.map((r) => el("tr", {}, ...r.map((c) => {
          const num = /^-?\d+(\.\d+)?/.test(c.replace(/[*↓↑\s]/g, ""));
          return el("td", num ? { class: "num", tabindex: "0", role: "button", onclick: () => showCell(ctx, c), onkeydown: (e) => { if (e.key === "Enter") showCell(ctx, c); } } : {}, ...renderInline(c, ctx));
        }))))));
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, "")); i++; }
      out.push(el("ul", {}, ...items.map((t) => el("li", {}, ...renderInline(t, ctx)))));
      continue;
    }
    if (REF.test(line)) {
      while (i < lines.length && REF.test(lines[i])) { out.push(el("p", { class: "ref" }, lines[i])); i++; }
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*\|)/.test(lines[i]) && !REF.test(lines[i])) { para.push(lines[i]); i++; }
    out.push(el("p", {}, ...renderInline(para.join(" "), ctx)));
  }
  return out;
}

function markClaims(md, claims) {
  let text = md;
  claims.forEach((c, i) => {
    const sentence = (c.claim || "").replace(/\.$/, "");
    if (sentence.length > 20 && text.includes(sentence)) text = text.replace(sentence, "\u0001" + i + "\u0002" + sentence + "\u0003");
  });
  return text;
}

function showSource(ctx, key) {
  const s = ctx.data.sources[key];
  ctx.side.replaceChildren(el("h3", {}, key + (s ? ": " + s.title : "")), s ? el("p", { class: "small" }, (s.authors || []).slice(0, 4).join(", ") + (s.year ? " (" + s.year + ")" : "")) : el("p", {}, "This source is not in the retrieval log."),
    s && s.url ? el("p", {}, el("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, "Open the paper")) : "");
}

function showClaim(ctx, i) {
  const c = ctx.data.claims[i];
  ctx.side.replaceChildren(el("h3", {}, "The evidence for this sentence"), el("p", { class: "small" }, "Source " + c.source_key + (c.locator ? ", " + c.locator : "")),
    el("blockquote", {}, c.quote), el("p", { class: "small" }, "Quote check: " + (c.quote_check || "not recorded")), el("button", { type: "button", onclick: () => showSource(ctx, c.source_key) }, "About the source"));
}

function leaves(obj, path = [], out = []) {
  if (obj && typeof obj === "object") for (const [k, v] of Object.entries(obj)) leaves(v, [...path, k], out);
  else if (typeof obj === "number") out.push([path.join(" › "), obj]);
  return out;
}

async function showCell(ctx, text) {
  const n = parseFloat(text.replace(/[^\d.\-eE]/g, " ").trim().split(/\s+/)[0]);
  if (!ctx.results) ctx.side.replaceChildren(el("p", { class: "small" }, "This document has no results file to look the number up in."));
  else {
    const hits = leaves(ctx.results).filter(([p, v]) => !p.endsWith("values") && Math.abs(v - n) <= Math.max(Math.abs(n) * 0.005, 0.0006)).slice(0, 6);
    ctx.side.replaceChildren(el("h3", {}, "Where " + text.trim() + " comes from"), hits.length ? el("ul", {}, ...hits.map(([p, v]) => el("li", { class: "small" }, p + " = " + v))) : el("p", { class: "small" }, "No result cell matches this number to the shown precision."));
  }
}

async function readerView(kind, id) {
  const base = kind === "example" ? "/api/examples/" + id : "/api/runs/" + id;
  const data = await api(base + "/paper");
  const ctx = { data, side: el("aside", { class: "side", "aria-live": "polite" }, el("h3", {}, "Evidence"), el("p", { class: "small" }, "Click a dotted sentence for its quote, a source number for the paper, or a table number for its results cell.")), fileBase: base + "/files/", results: null };
  if (kind === "example") { try { ctx.results = await api(base + "/files/results.json"); } catch (_) { /* a review has none */ } }
  const doc = el("article", { class: "paper" }, ...renderMarkdown(markClaims(data.markdown, data.claims), ctx));
  const audit = data.audit;
  const findings = (audit && audit.findings) || [];
  const leads = findings.filter((f) => /method|align|novel/i.test(f.check || ""));
  const real = findings.filter((f) => !leads.includes(f));
  const auditBox = el("section", { class: "appendix" }, el("h2", {}, "The audit"), el("p", {}, lightBadge(audit && audit.overall)),
    el("p", { class: "small" }, "Checks run: " + ((audit && audit.checks_run) || []).join(", ") + ". Green means the citations are real and each claim is supported by the passage it quotes. It does not mean the review is complete."),
    real.length ? el("ul", {}, ...real.map((f) => el("li", {}, "[" + f.severity + "] " + f.summary))) : el("p", {}, "No findings."),
    leads.length ? el("details", {}, el("summary", {}, "Leads for a person (" + leads.length + "): a warning here is a lead, not a verdict"), el("ul", {}, ...leads.map((f) => el("li", {}, "[" + f.severity + "] " + f.summary)))) : "");
  const title = kind === "example" ? data.example.title : shortTitle(await titleOf(id));
  const byline = el("div", { class: "byline" }, lightBadge(audit && audit.overall));
  if (kind === "example") byline.append("Spent " + money(data.example.spent_usd) + " of a " + money(data.example.budget_cap_usd) + " cap");
  const head = el("header", { class: "doc-head" },
    el("p", { class: "kicker" }, kind === "example" ? (data.example.kind === "paper" ? "Example · research paper" : "Example · literature review") : "Literature review"),
    el("h1", {}, title), byline,
    el("div", { class: "row" }, el("a", { class: "button primary", href: base + "/pdf" }, "Download PDF"), el("a", { class: "button", href: kind === "example" ? "#/examples" : "#/run/" + id }, kind === "example" ? "All examples" : "Back to the run")));
  if (kind === "example") head.append(el("p", { class: "small" }, data.example.outcome));
  return [head, el("div", { class: "cols" }, el("div", {}, doc, auditBox), ctx.side)];
}

/* ── start ─────────────────────────────────────────────────────────────── */

loadBasics().then(route).catch((e) => main.replaceChildren(el("p", { class: "error", role: "alert" }, "The app could not start: " + e.message)));

"""Reading: open-access PDFs to evidence passages (T3: GROBID for references and prose; Docling only where needed).

For the candidates that passed the relevance screen the stage reads **abstracts for all of them and full text for the
top K by rank** where an open-access PDF exists. A PDF is fetched politely (arXiv asks for one request per three
seconds) and cached by URL; GROBID turns it into TEI, whose body paragraphs become **passages** with locators; the parse
is cached by the PDF's hash and the parser's name. The passages most relevant to the question (a small BM25 over the
paper's own passages, no model call) are the only text the synthesis may quote.

`quote_in_text` is the deterministic quote check the claim checks use: a quote is real when it is a verbatim span of the
passage after whitespace, hyphenation, quotation-mark and ligature normalisation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Protocol

import httpx

TEI = {"t": "http://www.tei-c.org/ns/1.0"}
MAX_PDF_BYTES = 30_000_000
PASSAGES_PER_PAPER = 5
MIN_PASSAGE_WORDS, MAX_PASSAGE_WORDS = 40, 220
MIN_QUOTE_CHARS = 25  # a quote shorter than this proves nothing
SKIP_HEADS = re.compile(r"reference|acknowledg|appendix|supplementary|bibliograph", re.IGNORECASE)
STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were with we our "
           "can how does do not than then into their these those which who will would should may might also more most "
           "such using used use between when where while".split())  # fmt: skip


# ── quote normalisation ──────────────────────────────────────────────────────────────────────────────

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                         "−": "-", "­": "", " ": " "})  # fmt: skip


def norm_for_quote(text: str) -> str:
    """Whitespace, hyphenation, quotation marks and ligatures normalised; case folded."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # a word hyphenated across a line break
    return " ".join(text.split()).casefold()


def quote_in_text(quote: str, text: str) -> bool:
    q = norm_for_quote(quote).strip(" .\"'")
    return len(q) >= MIN_QUOTE_CHARS and q in norm_for_quote(text)


# ── fetching and parsing ─────────────────────────────────────────────────────────────────────────────


class PdfFetcher:
    """GET a PDF, paced and cached by URL. Returns the bytes, or None with a reason in `last_error`."""

    def __init__(self, directory: Path, client: httpx.Client | None = None, *, pace: bool = True) -> None:
        self.directory, self.pace = directory, pace
        agent = "VERA-research/0.1 (+https://github.com/PCSchmidt/VERA; reading)"
        self.client = client or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": agent})
        self.last_error: str | None = None
        self._last = -1e9

    def __call__(self, url: str) -> bytes | None:
        self.last_error = None
        path = self.directory / f"{hashlib.sha1(url.encode()).hexdigest()[:20]}.pdf"
        if path.exists():
            return path.read_bytes()
        for attempt in range(3):
            if self.pace:
                wait = 3.1 - (time.monotonic() - self._last)
                if wait > 0:
                    time.sleep(wait)
            self._last = time.monotonic()
            try:
                resp = self.client.get(url)
            except httpx.TransportError as exc:
                self.last_error = f"transport error {type(exc).__name__}"
            else:
                if resp.status_code in {429, 500, 502, 503, 504}:
                    self.last_error = f"HTTP {resp.status_code}"
                elif resp.is_error:
                    self.last_error = f"HTTP {resp.status_code}"
                    return None
                elif len(resp.content) > MAX_PDF_BYTES or not resp.content.startswith(b"%PDF"):
                    self.last_error = "not a PDF or too large"
                    return None
                else:
                    self.directory.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(resp.content)
                    return resp.content
            time.sleep(3 * (attempt + 1) if self.pace else 0)
        return None


class Parser(Protocol):
    name: str

    def __call__(self, pdf: bytes) -> list[tuple[str, str]]: ...  # [(section heading, paragraph text)]


class GrobidParser:
    """GROBID's full-text service (docker: lfoppiano/grobid:0.8.2): the body's paragraphs with their section heads."""

    name = "grobid-0.8.2"

    def __init__(self, url: str = "http://localhost:8070/api/processFulltextDocument",
                 client: httpx.Client | None = None) -> None:  # fmt: skip
        self.url = url
        self.client = client or httpx.Client(timeout=180)

    def __call__(self, pdf: bytes) -> list[tuple[str, str]]:
        resp = self.client.post(self.url, files={"input": ("paper.pdf", pdf, "application/pdf")})
        resp.raise_for_status()
        return paragraphs_from_tei(resp.text)

    def references(self, pdf: bytes) -> list[dict]:
        """The PDF's reference list (GROBID's reference service: T3's reason for choosing it)."""
        resp = self.client.post(self.url.replace("processFulltextDocument", "processReferences"),
                                files={"input": ("paper.pdf", pdf, "application/pdf")})  # fmt: skip
        resp.raise_for_status()
        return references_from_tei(resp.text)


def _tei_text(el: ET.Element | None) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def references_from_tei(tei: str) -> list[dict]:
    """The reference list of a GROBID TEI document: title, authors, year, DOI and arXiv id where it found them."""
    out = []
    try:
        root = ET.fromstring(tei)
    except ET.ParseError:  # GROBID answered with nothing (found in Increment 4 on one PDF): no references, not a crash
        return []
    for b in root.findall(".//t:listBibl/t:biblStruct", TEI):
        analytic = b.find("t:analytic/t:title", TEI)
        title = _tei_text(analytic) or _tei_text(b.find("t:monogr/t:title", TEI))
        authors = []
        for a in b.findall(".//t:author/t:persName", TEI):
            first = " ".join(_tei_text(f) for f in a.findall("t:forename", TEI))
            authors.append(f"{first} {_tei_text(a.find('t:surname', TEI))}".strip())
        date = b.find(".//t:imprint/t:date", TEI)
        year = ((date.get("when") or _tei_text(date))[:4]) if date is not None else ""
        ids = {(i.get("type") or "").lower(): _tei_text(i) for i in b.findall(".//t:idno", TEI)}
        if title:
            out.append({"title": title, "authors": authors, "year": year, "doi": ids.get("doi", ""),
                        "arxiv": ids.get("arxiv", "")})  # fmt: skip
    return out


def paragraphs_from_tei(tei: str) -> list[tuple[str, str]]:
    root = ET.fromstring(tei)
    out: list[tuple[str, str]] = []
    for div in root.findall(".//t:text/t:body//t:div", TEI):
        head_el = div.find("t:head", TEI)
        head = " ".join("".join(head_el.itertext()).split()) if head_el is not None else ""
        for p in div.findall("t:p", TEI):
            text = " ".join("".join(p.itertext()).split())
            if text:
                out.append((head, text))
    return out


class ParseCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def parse(self, pdf: bytes, parser: Parser) -> list[tuple[str, str]]:
        path = self.directory / f"{hashlib.sha256(pdf).hexdigest()[:24]}.{parser.name}.json"
        if path.exists():
            return [tuple(x) for x in json.loads(path.read_text(encoding="utf-8"))]
        paragraphs = parser(pdf)
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(paragraphs), encoding="utf-8")
        return paragraphs

    def references(self, pdf: bytes, parser) -> list[dict]:
        """The reference list GROBID finds in the PDF, cached beside the paragraphs."""
        path = self.directory / f"{hashlib.sha256(pdf).hexdigest()[:24]}.{parser.name}.refs.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        refs = parser.references(pdf)
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(refs), encoding="utf-8")
        return refs


# ── passages ─────────────────────────────────────────────────────────────────────────────────────────


def build_passages(paragraphs: list[tuple[str, str]], key: str) -> list[dict]:
    """Passages of 40-220 words with locators, from (heading, paragraph) pairs; reference and appendix sections skipped.
    Short paragraphs join the next one in the same section; long ones are cut at sentence boundaries."""
    units: list[tuple[str, str, int]] = []  # (heading, text, paragraph number)
    for n, (head, text) in enumerate(paragraphs, start=1):
        if SKIP_HEADS.search(head or ""):
            continue
        units.append((head, text, n))
    passages: list[dict] = []
    buf: list[str] = []
    buf_head, buf_n = "", 0

    def flush() -> None:
        nonlocal buf, buf_head, buf_n
        if buf:
            where = f"sec. {buf_head or 'body'}, para {buf_n}"
            passages.append({"source_key": key, "id": f"{key}-P{len(passages) + 1}", "kind": "fulltext",
                             "locator": where, "text": " ".join(buf)})  # fmt: skip
        buf, buf_head, buf_n = [], "", 0

    for head, text, n in units:
        for piece in _split_sentences(text):
            if not buf:
                buf_head, buf_n = head, n
            elif head != buf_head:
                flush()
                buf_head, buf_n = head, n
            buf.append(piece)
            if sum(len(b.split()) for b in buf) >= MIN_PASSAGE_WORDS:
                flush()
    flush()
    return passages


def _split_sentences(text: str) -> list[str]:
    """Sentences, regrouped so that no piece exceeds MAX_PASSAGE_WORDS."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", text)
    pieces, cur = [], ""
    for s in sentences:
        if cur and len((cur + " " + s).split()) > MAX_PASSAGE_WORDS:
            pieces.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2]


def rank_passages(passages: list[dict], query: str, top: int = PASSAGES_PER_PAPER) -> list[dict]:
    """The `top` passages most relevant to `query`, by BM25 over this paper's own passages (stable on ties)."""
    if not passages:
        return []
    docs = [Counter(_tokens(p["text"])) for p in passages]
    avg = sum(sum(d.values()) for d in docs) / len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    q = Counter(_tokens(query))
    scores = []
    for i, d in enumerate(docs):
        length = sum(d.values())
        s = 0.0
        for term in q:
            if term in d:
                idf = math.log(1 + (len(docs) - df[term] + 0.5) / (df[term] + 0.5))
                s += idf * d[term] * 2.2 / (d[term] + 1.2 * (0.25 + 0.75 * length / max(avg, 1)))
        scores.append((-s, i))
    return [passages[i] for _, i in sorted(scores)[:top]]


def abstract_passage(record: dict) -> dict | None:
    abstract = (record.get("abstract") or "").strip()
    if not abstract:
        return None
    return {"source_key": record["key"], "id": f"{record['key']}-A", "kind": "abstract", "locator": "abstract",
            "text": abstract}  # fmt: skip

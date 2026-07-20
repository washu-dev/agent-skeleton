"""ZONE 2 — System prompt + result normalization.  ★ WRITE THIS ★

- SYSTEM_PROMPT: the instructions that define your agent's behavior and the exact
  output contract you want from the model.
- normalize_result(): turn the model's final text into the STABLE structured dict
  your agent returns.

Why a stable shape matters: the planner reads the structured DataPart artifact your
agent emits, so downstream callers depend on these keys always existing.
"""
from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = (
    "You are research-atlas, an academic literature-search assistant. Given a "
    "research topic or question, your job is to search REAL academic sources and "
    "return an organized, trustworthy reading list that helps a researcher get "
    "oriented in unfamiliar literature.\n"
    "\n"
    "You have three search tools:\n"
    "  - search_arxiv: preprints, best for math/physics/CS/statistics; NOT "
    "peer-reviewed.\n"
    "  - search_crossref: published, peer-reviewed works across all fields, with "
    "citation counts and DOIs; rarely has abstracts.\n"
    "  - search_openalex: broadest coverage incl. humanities/social science, "
    "includes abstracts and citation counts; a good fallback.\n"
    "\n"
    "HOW TO WORK:\n"
    "1. Decide which source(s) fit the query. For technical/STEM topics start with "
    "arxiv and/or crossref; for social science or humanities prefer openalex; when "
    "in doubt use two complementary sources. You may call tools more than once with "
    "refined queries.\n"
    "2. Organize the papers you ACTUALLY retrieved into a few coherent themes.\n"
    "3. Note where findings appear to conflict or disagree, and be explicit about "
    "gaps — what you searched for but did not find, or what you cannot verify.\n"
    "\n"
    "TRUST RULES (these are non-negotiable):\n"
    "  - Cite ONLY papers that were actually returned by a tool call. NEVER invent "
    "a title, author, year, DOI, or link.\n"
    "  - Every paper you list must carry the metadata the tool returned (title, "
    "authors, year, source, url/doi, citation_count when available).\n"
    "  - If a search returns nothing relevant, or all searches fail, say so plainly "
    "in 'gaps' and return empty themes rather than fabricating results.\n"
    "  - Do not overstate. If you are unsure two papers truly conflict, describe "
    "the tension tentatively rather than asserting it.\n"
    "\n"
    "OUTPUT: Return ONLY a valid JSON object (no prose, no markdown fences) with "
    "these keys:\n"
    '  topic (string): the topic/question you searched.\n'
    '  summary (string): 2-4 sentences orienting the reader.\n'
    '  themes (array): objects {theme (string), papers (array)} where each paper is '
    '{title, authors (array of strings), year (number or null), source (string), '
    'url (string), doi (string or null), citation_count (number or null), note '
    '(string: why this paper matters / how it fits the theme)}.\n'
    '  conflicts (array of strings): conflicting or contested findings across the '
    'papers; empty array if none observed.\n'
    '  gaps (array of strings): what could not be found or verified; empty if none.\n'
    '  sources_searched (array of strings): which tools you called.\n'
)


# The stable keys every result carries, so downstream callers never KeyError.
_EMPTY_RESULT = {
    "topic": "",
    "summary": "",
    "themes": [],
    "conflicts": [],
    "gaps": [],
    "sources_searched": [],
}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _render_text(data: dict[str, Any]) -> str:
    """Build the human-readable A2A message from the structured fields."""
    lines: list[str] = []
    topic = str(data.get("topic") or "").strip()
    lines.append(f"Reading list for: {topic}" if topic else "Reading list")

    summary = str(data.get("summary") or "").strip()
    if summary:
        lines.append("")
        lines.append(summary)

    for theme in _as_list(data.get("themes")):
        if not isinstance(theme, dict):
            continue
        lines.append("")
        lines.append(f"## {str(theme.get('theme') or 'Theme').strip()}")
        for paper in _as_list(theme.get("papers")):
            if not isinstance(paper, dict):
                continue
            authors = _as_list(paper.get("authors"))
            author_str = ", ".join(str(a) for a in authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            year = paper.get("year")
            cites = paper.get("citation_count")
            bits = [b for b in [author_str, str(year) if year else ""] if b]
            meta = f" ({'; '.join(bits)})" if bits else ""
            if isinstance(cites, int):
                meta += f" — {cites} citations"
            lines.append(f"- {str(paper.get('title') or 'Untitled').strip()}{meta}")
            url = str(paper.get("url") or "").strip()
            if url:
                lines.append(f"  {url}")
            note = str(paper.get("note") or "").strip()
            if note:
                lines.append(f"  {note}")

    conflicts = [str(c).strip() for c in _as_list(data.get("conflicts")) if str(c).strip()]
    if conflicts:
        lines.append("")
        lines.append("## Conflicting / contested findings")
        lines.extend(f"- {c}" for c in conflicts)

    gaps = [str(g).strip() for g in _as_list(data.get("gaps")) if str(g).strip()]
    if gaps:
        lines.append("")
        lines.append("## Gaps & caveats")
        lines.extend(f"- {g}" for g in gaps)

    return "\n".join(lines).strip()


def normalize_result(raw_text: str, tool_log: list[dict[str, Any]]) -> dict[str, Any]:
    """Coerce the model's final text into a stable result dict.

    Always returns the same keys (topic, summary, themes, conflicts, gaps,
    sources_searched, tools_used, response_text) so downstream callers can rely
    on them even when the model returns malformed JSON.
    """
    text = (raw_text or "").strip()

    # Tolerate ```json fences around the JSON.
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]

    data: dict[str, Any] = {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            data = parsed
    except (ValueError, TypeError):
        data = {}

    # Which tools actually ran (ground truth from the loop, not the model's claim).
    tools_used = sorted({str(call.get("name")) for call in tool_log if call.get("name")})

    result: dict[str, Any] = dict(_EMPTY_RESULT)
    result.update(
        {
            "topic": str(data.get("topic") or "").strip(),
            "summary": str(data.get("summary") or "").strip(),
            "themes": _as_list(data.get("themes")),
            "conflicts": [str(c) for c in _as_list(data.get("conflicts"))],
            "gaps": [str(g) for g in _as_list(data.get("gaps"))],
            "sources_searched": [str(s) for s in _as_list(data.get("sources_searched"))] or tools_used,
            "tools_used": tools_used,
        }
    )

    # If the model failed to produce parseable JSON, degrade honestly: surface the
    # raw text and flag that structuring failed, rather than pretending success.
    if not data:
        result["gaps"] = ["The agent could not produce a structured result for this query."]
        result["response_text"] = text or "(no answer produced)"
    else:
        result["response_text"] = _render_text(result) or text or "(no answer produced)"

    return result

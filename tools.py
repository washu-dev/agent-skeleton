"""ZONE 4 — Tool dispatch + tool bodies.  ★ WRITE THE BODIES ★ (dispatch is copy)

- Tool BODIES (word_count, reverse_text): your real Python — replace them with
  your agent's actual capabilities. Each takes keyword args named exactly like
  its schema `properties` and returns a JSON-able dict.
- TOOL_REGISTRY: the {name: function} map. This REPLACES a hand-written if/elif
  tool chain. Adding a tool = write a function + add one registry entry + add one
  schema in tool_schemas.py. The LLM loop dispatches over this registry via
  ``AgentSpec.dispatch`` (see spec.py).
- validate_tool_registry(): a startup alignment check many hand-rolled agents
  lack. It fails fast if a schema and its function disagree, instead of failing
  silently at runtime as `{"ok": False, "error": ...}`.
"""
from __future__ import annotations

import inspect
import re
import xml.etree.ElementTree as ET
from typing import Any, Callable

import requests

from .tool_schemas import TOOL_SCHEMAS


# --- HTTP helpers --------------------------------------------------------
# A short, honest User-Agent. OpenAlex asks callers to identify themselves;
# a contact address gets us into their faster "polite pool".
_USER_AGENT = "research-atlas/0.1 (WashU DTRC hackathon; mailto:c.israel@wustl.edu)"
_TIMEOUT = 20  # seconds; every external call is bounded so the loop can't hang.


def _clamp_results(max_results: int) -> int:
    """Keep result counts sane regardless of what the model asks for."""
    try:
        n = int(max_results)
    except (TypeError, ValueError):
        return 5
    return max(1, min(n, 25))


# --- Tool bodies  ★ WRITE THESE ★ ----------------------------------------

def search_arxiv(*, query: str, max_results: int = 5) -> dict[str, Any]:
    """Query the arXiv Atom API and return a list of preprints."""
    n = _clamp_results(max_results)
    try:
        resp = requests.get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": n,
                "sortBy": "relevance",
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"ok": False, "source": "arxiv", "error": f"{type(exc).__name__}: {exc}"}

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        return {"ok": False, "source": "arxiv", "error": f"XML parse error: {exc}"}

    papers: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        arxiv_url = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_url else arxiv_url
        title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
        abstract = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
        year = published[:4] if len(published) >= 4 and published[:4].isdigit() else None
        papers.append(
            {
                "title": title,
                "authors": [a for a in authors if a],
                "year": int(year) if year else None,
                "abstract": abstract,
                "url": arxiv_url,
                "arxiv_id": arxiv_id,
                "citation_count": None,  # arXiv does not provide citations
                "source": "arxiv",
                "peer_reviewed": False,  # preprint server
            }
        )

    return {"ok": True, "source": "arxiv", "count": len(papers), "papers": papers}


def search_crossref(
    *, query: str, year_from: int | None = None, max_results: int = 5
) -> dict[str, Any]:
    """Query the Crossref REST API and return matching published works."""
    n = _clamp_results(max_results)
    params: dict[str, Any] = {
        "query": query,
        "rows": n,
        "select": "title,author,issued,DOI,is-referenced-by-count,abstract",
        # Identify ourselves for Crossref's faster "polite pool".
        "mailto": "c.israel@wustl.edu",
    }
    if year_from is not None:
        try:
            params["filter"] = f"from-pub-date:{int(year_from)}-01-01"
        except (TypeError, ValueError):
            pass  # ignore a non-numeric year rather than failing the search

    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params=params,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "source": "crossref", "error": f"{type(exc).__name__}: {exc}"}
    except ValueError as exc:
        return {"ok": False, "source": "crossref", "error": f"JSON parse error: {exc}"}

    papers: list[dict[str, Any]] = []
    for item in (data.get("message") or {}).get("items") or []:
        doi = item.get("DOI")
        title = " ".join((item.get("title") or [""])[0].split()) if item.get("title") else ""
        authors = [
            " ".join(part for part in [a.get("given"), a.get("family")] if part).strip()
            for a in (item.get("author") or [])
        ]
        # 'issued' -> date-parts: [[year, month, day]]
        date_parts = (item.get("issued") or {}).get("date-parts") or [[]]
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        # Crossref abstracts, when present, are JATS XML; strip the tags.
        abstract = item.get("abstract") or ""
        if abstract:
            abstract = " ".join(re.sub(r"<[^>]+>", " ", abstract).split())
        papers.append(
            {
                "title": title,
                "authors": [a for a in authors if a],
                "year": year,
                "abstract": abstract,
                "url": f"https://doi.org/{doi}" if doi else "",
                "doi": doi,
                "citation_count": item.get("is-referenced-by-count"),
                "source": "crossref",
            }
        )

    return {"ok": True, "source": "crossref", "count": len(papers), "papers": papers}


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]}; rebuild it."""
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            positioned.append((pos, word))
    positioned.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positioned)


def search_openalex(*, query: str, max_results: int = 5) -> dict[str, Any]:
    """Query the OpenAlex works API and return matching scholarly works."""
    n = _clamp_results(max_results)
    try:
        resp = requests.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": n},
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "source": "openalex", "error": f"{type(exc).__name__}: {exc}"}
    except ValueError as exc:
        return {"ok": False, "source": "openalex", "error": f"JSON parse error: {exc}"}

    papers: list[dict[str, Any]] = []
    for item in data.get("results") or []:
        doi = item.get("doi")  # already a full https://doi.org/... URL when present
        authors = [
            (auth.get("author") or {}).get("display_name", "").strip()
            for auth in (item.get("authorships") or [])
        ]
        papers.append(
            {
                "title": item.get("title") or item.get("display_name") or "",
                "authors": [a for a in authors if a],
                "year": item.get("publication_year"),
                "abstract": _reconstruct_abstract(item.get("abstract_inverted_index")),
                "url": doi or item.get("id") or "",
                "doi": doi,
                "citation_count": item.get("cited_by_count"),
                "source": "openalex",
            }
        )

    return {"ok": True, "source": "openalex", "count": len(papers), "papers": papers}


# --- Registry (one entry per tool)  ★ EDIT ★ -----------------------------

TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "search_arxiv": search_arxiv,
    "search_crossref": search_crossref,
    "search_openalex": search_openalex,
}


# --- The alignment check -----------------

def validate_tool_registry(
    schemas: list[dict[str, Any]] | None = None,
    registry: dict[str, Callable[..., dict[str, Any]]] | None = None,
) -> None:
    """Fail fast if schemas and functions disagree. Called by serve.create_app.

    For every tool it checks that:
      * the schema `name` has a function (and every function has a schema);
      * every schema property is a keyword parameter of the function;
      * every OPTIONAL property's parameter carries a default (so the model may
        omit it without a TypeError at call time);
      * the function has no required parameter that the schema does not declare.
    A function may declare **kwargs to opt out of the strict parameter checks.

    Raises ValueError listing ALL problems; returns None when everything aligns.
    """
    schemas = TOOL_SCHEMAS if schemas is None else schemas
    registry = TOOL_REGISTRY if registry is None else registry

    problems: list[str] = []
    schema_names: list[str] = []

    for schema in schemas:
        fn_spec = schema.get("function") or {}
        name = str(fn_spec.get("name") or "")
        if not name:
            problems.append("a schema entry is missing function.name")
            continue
        schema_names.append(name)

        params = fn_spec.get("parameters") or {}
        props = set((params.get("properties") or {}).keys())
        required = set(params.get("required") or [])

        fn = registry.get(name)
        if fn is None:
            problems.append(f"[{name}] schema has no function in TOOL_REGISTRY")
            continue

        sig = inspect.signature(fn)
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            continue  # function opts out of strict checks via **kwargs

        fn_params = {
            n: p
            for n, p in sig.parameters.items()
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        fn_required = {n for n, p in fn_params.items() if p.default is inspect.Parameter.empty}

        # schema -> function
        for prop in sorted(props):
            if prop not in fn_params:
                problems.append(f"[{name}] schema property '{prop}' is not a parameter of {fn.__name__}()")
        for prop in sorted(props - required):
            if prop in fn_params and fn_params[prop].default is inspect.Parameter.empty:
                problems.append(f"[{name}] optional property '{prop}' must have a default in {fn.__name__}()")
        # function -> schema
        for pname in sorted(fn_params):
            if pname not in props:
                problems.append(f"[{name}] {fn.__name__}() parameter '{pname}' is not declared in the schema")
        for pname in sorted(fn_required):
            if pname not in required:
                problems.append(f"[{name}] {fn.__name__}() requires '{pname}' but the schema does not mark it required")

    for name in registry:
        if name not in schema_names:
            problems.append(f"[{name}] function in TOOL_REGISTRY has no schema in TOOL_SCHEMAS")

    if problems:
        raise ValueError("Tool schema/function alignment failed:\n  - " + "\n  - ".join(problems))

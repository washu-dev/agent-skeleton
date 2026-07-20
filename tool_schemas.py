"""ZONE 1 — Tool schemas.  ★ WRITE THIS ★

The list of tools your LLM may call, in OpenAI **Chat Completions** shape:

    {"type": "function",
     "function": {"name": ..., "description": ..., "parameters": <JSON Schema>}}

This is the standard OpenAI Chat Completions tool shape.

Two rules the startup check enforces (tools.validate_tool_registry):
  1. Every `name` here has a matching function in tools.py's TOOL_REGISTRY.
  2. The `parameters` here match that function's signature — each schema
     property is a keyword arg of the function; required properties may or may
     not have a default; OPTIONAL properties must have a default.

So the schema and the Python signature are two views of one thing. (If you ever
want this to be impossible to get wrong, generate these schemas FROM the typed
functions instead — see CLAUDE.md "Closing the gap further".)
"""
from __future__ import annotations

from typing import Any

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": (
                "Search arXiv for academic preprints and papers. Best for math, "
                "physics, computer science, quantitative biology, statistics, and "
                "related quantitative fields. Returns paper titles, authors, "
                "abstracts, arXiv IDs, and links. Note: arXiv is a preprint server, "
                "so results may not be peer-reviewed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. a topic, keywords, or research question.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (default 5).",
                    },
                },
                # 'max_results' is optional -> its function parameter carries a default.
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_crossref",
            "description": (
                "Search Crossref, the authoritative catalog of published, peer-reviewed "
                "scholarly works (journal articles, conference papers, books) across all "
                "fields. Provides citation counts and DOIs, which help gauge influence "
                "and cite sources precisely. Returns titles, authors, publication year, "
                "citation counts, DOIs, and links. Good default for peer-reviewed "
                "literature. Note: Crossref rarely includes abstracts — use "
                "search_openalex if you also need abstract text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. a topic, keywords, or research question.",
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "If set, only return papers published in or after this year.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (default 5).",
                    },
                },
                # 'year_from' and 'max_results' are optional -> their function
                # parameters carry defaults.
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_openalex",
            "description": (
                "Search OpenAlex, an open catalog of scholarly works with the broadest "
                "coverage including humanities and social sciences. Use as a fallback "
                "when arXiv or Semantic Scholar return little, or for non-STEM topics. "
                "Returns titles, authors, abstracts, publication year, citation counts, "
                "DOIs, and links."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. a topic, keywords, or research question.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (default 5).",
                    },
                },
                # 'max_results' is optional -> its function parameter carries a default.
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]

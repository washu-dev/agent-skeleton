"""Entry-point shim: keeps ``python -m agent_skeleton.serve …`` working.

The CLI and app factory now live in ``agent_skeleton.core.serve`` (the frozen
engine). This module forwards to them so the documented commands are unchanged:

    python -m agent_skeleton.serve check          # validate schemas <-> functions
    python -m agent_skeleton.serve serve-a2a      # OPTION 2: run the tool-loop agent
    python -m agent_skeleton.serve serve-handler \\
        --file handler.py --class MyHandler       # OPTION 3: run a custom handler

``create_app`` / ``load_agent_card`` are re-exported for callers that build an app
in their own script (``from agent_skeleton.serve import create_app``).
"""
from __future__ import annotations

from .core.serve import create_app, load_agent_card, main

__all__ = ["create_app", "load_agent_card", "main"]

if __name__ == "__main__":
    main()

"""agent_skeleton.custom — OPTION 3: wrap your own code as a handler.

You do NOT rewrite your code — you add one thin adapter: a subclass of
``AgentHandler`` implementing ``handle_structured()``, which returns a dict with an
``"answer"`` key. ``HandlerExecutor`` wraps it in the A2A protocol (heartbeat,
runtime cap, file decoding, credential injection).

  base.py             — the AgentHandler contract you subclass + FileInput
  handler_executor.py — HandlerExecutor: wraps any AgentHandler for A2A
  INTEGRATION_GUIDE.md — the full walkthrough (the 6 questions, deps, a worked example)

Run one locally with:
    python -m agent_skeleton.serve serve-handler --file handler.py --class MyHandler

See custom/README.md for the overview.
"""
from __future__ import annotations

from .base import AgentHandler, FileInput

__all__ = ["AgentHandler", "FileInput"]

# HandlerExecutor pulls in the a2a_runtime guard; import defensively so importing
# this package never hard-fails when the optional serving deps are absent.
try:
    from .handler_executor import HandlerExecutor

    __all__ += ["HandlerExecutor"]
except ImportError:
    pass

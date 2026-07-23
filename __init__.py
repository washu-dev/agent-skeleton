"""agent_skeleton — a copy-to-start template for building an A2A agent.

The skeleton hands you the ~70% of every agent that is plumbing (the LLM loop, the
A2A server wiring, request parsing, the dual-channel response) and asks you to write
only the ~30% that is *your* agent. It offers **three ways** to build, each in its
own self-describing folder:

  endpoint_wrapper/ — OPTION 1: wrap an existing HTTP/API endpoint.
       Point an LLM loop at a running service; write NO code. The model turns each
       request into a call and reads the reply. See endpoint_wrapper/README.md.

  tool_loop/        — OPTION 2: an LLM tool loop you fill in.
       Supply typed @tool functions (tools.py) + a system prompt (prompt.py); a
       frozen engine runs the model-calls-tools loop. (The registration service can
       also generate this infrastructure for you.) See tool_loop/README.md.

  custom/           — OPTION 3: wrap your own code.
       Subclass AgentHandler and implement one method; the framework wraps it in an
       A2A server. Best when you already have working code. See custom/README.md.

  core/             — the frozen engine shared by all three (don't edit): the tool
       loop, AgentSpec, the @tool schema deriver, the A2A executors, and serve.py.

See README.md for the walkthrough and CLAUDE.md for working notes.

Exposed API:
    tool, collect_tools                              — define typed tool_loop tools
    AgentSpec, default_demo_spec, llm_wrapper_spec   — the spec engine (core)
    AgentHandler, FileInput, HandlerExecutor         — custom-code handlers (custom)
"""
from __future__ import annotations

from .core.spec import AgentSpec, default_demo_spec, llm_wrapper_spec
from .core.tool_engine import collect_tools, tool

__all__ = [
    "tool",
    "collect_tools",
    "AgentSpec",
    "default_demo_spec",
    "llm_wrapper_spec",
]

# Custom-code handler API (OPTION 3). Imported defensively so the tool_loop engine
# still imports (and `serve check` still runs) even if the custom modules are absent.
try:
    from .custom.base import AgentHandler, FileInput
    from .custom.handler_executor import HandlerExecutor

    __all__ += ["AgentHandler", "FileInput", "HandlerExecutor"]
except ImportError:
    pass

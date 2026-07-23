# OPTION 2 — an LLM tool loop

This is the path where **the agent's value is reasoning**: the model decides which
tool to call, chains calls, and synthesizes an answer. You supply a system prompt and
a set of tools; the frozen engine in [`../core/`](../core/) runs the
model-calls-tools loop. You write no server, protocol, or loop code.

Use this path when the work is best expressed as *"give the model these capabilities
and let it figure out how to combine them."* If you instead have a running service to
expose, use [`../endpoint_wrapper/`](../endpoint_wrapper/README.md); if you have
working code to wrap, use [`../custom/`](../custom/README.md).

## What you edit

There are exactly two "write" files in this folder (plus the shared
[`../agent.card.json`](../agent.card.json) for your agent's identity):

| File | You write |
|---|---|
| [`tools.py`](tools.py) | your tools, as typed `@tool` functions, returned from `build_tools(config)` — the schema is **derived** from each function |
| [`prompt.py`](prompt.py) | `SYSTEM_PROMPT` + `normalize_result()` (the stable output shape callers depend on) |

## Tools: one typed function, no separate schema

Each tool is a typed function decorated with `@tool`. **`@tool` reads the function's
signature + type hints + docstring and *derives* the JSON schema the model sees** — so
there's no separate schema to hand-write, and it can't drift from the code.

Define all your tools inside `build_tools(config)`. The factory closes over your
agent's `config`, so any secret or handle in it (an API key, a DB connection, a
tenant id) is baked into every tool **once** and is never shown to or set by the LLM —
it isn't a parameter, so it never reaches the schema:

```python
def build_tools(config):
    @tool
    def word_count(*, text: str) -> dict:            # tool "word_count"
        """Count the words in a piece of text."""    # -> description; params: {text: string}
        return {"ok": True, "count": len(text.split())}

    @tool(name="web_search")
    def web_search(*, query: str, max_results: int = 5) -> dict:
        """Search the web for a query."""
        # config["search_api_key"] is baked in — the LLM only sets query/max_results
        return _search(query, max_results, api_key=config["search_api_key"])

    return [word_count, web_search]
```

`collect_tools(build_tools(config))` produces the `TOOL_SCHEMAS` + `TOOL_REGISTRY`
the engine runs — one source of truth (the demo `tools.py` already wires this up).

## Verify and run

```bash
python -m agent_skeleton.serve check       # validates schemas <-> functions (no deps, no LLM)
python -m agent_skeleton.serve serve-a2a   # runs the agent over A2A (needs a2a-sdk + uvicorn)
```

`serve check` is the safety net: it fails fast if a schema and its function disagree,
in both directions, so you never discover a mismatch at runtime.

For an LLM: set `OPENAI_API_KEY` (any non-empty placeholder for a local vLLM) and
optionally `OPENAI_BASE_URL`. Against vLLM, launch it with `--enable-auto-tool-choice
--tool-call-parser <parser>`, or the model silently stops calling tools.

## Preset tools ([`system_tools/`](system_tools/))

Instead of writing tool bodies, you can arm an LLM wrapper with ready-made **preset
tools** chosen by name from the built-in catalog (`calculator`, `current_time`, …).
Build the spec in your own script and hand it to `create_app`:

```python
from agent_skeleton import llm_wrapper_spec
spec = llm_wrapper_spec(
    name="My Agent",
    system_prompt="You are ...",
    preset_tools=["calculator", "current_time"],   # from tool_loop/system_tools
)
# from agent_skeleton.serve import create_app, load_agent_card
# app = create_app(load_agent_card("../agent.card.json"), spec=spec)  # serve under uvicorn
```

Preset tools are deliberately pure and dependency-free (no network, no secrets); see
[`system_tools/__init__.py`](system_tools/__init__.py) for the rules on adding to the
catalog.

## Two ways to fill in this path

1. **Edit the designated files here** — `tools.py` + `prompt.py`, as above. Fully
   self-contained; test it locally with `serve check` / `serve-a2a`.
2. **Through the registration service** — you supply just the tool bodies, schemas,
   and system prompt, and the service generates the surrounding infrastructure (the
   loop, the A2A server, the card) for you. Same engine, same contract — you provide
   only the ~30% that is your agent.

## How it flows through the engine

`tools.py` + `prompt.py` are assembled into an `AgentSpec` (see
[`../core/spec.py`](../core/spec.py)) — prompt, tool schemas, tool dispatch, and
normalize as **data**. `SkeletonAgentExecutor` (the A2A boundary) hands that spec to
`run_agent` in [`../core/llm_loop.py`](../core/llm_loop.py). The loop core stays
frozen and generic; only your spec changes. That separation is why you can unit-test
your tool bodies and run `serve check` with no network and no `a2a-sdk` installed.

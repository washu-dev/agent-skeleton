# agent_skeleton

A small, copy-to-start template for building an **A2A agent**. It hands you the
~70% of every agent that is plumbing (the LLM loop, the A2A server wiring, request
parsing, the dual-channel response) so you only write the part that is *your* agent.

That plumbing is the frozen engine in [`core/`](core/); it's shared and you rarely
touch it. Everything you *do* touch lives in one of **three self-describing folders,
one per way to build** — pick the one that matches what you have:

| You have… | Pick | Folder | You write |
|---|---|---|---|
| a running HTTP/API service to expose | **Wrap an endpoint** | [`endpoint_wrapper/`](endpoint_wrapper/README.md) | nothing — just point the loop at your URL |
| a task best solved by an LLM calling tools | **LLM tool loop** | [`tool_loop/`](tool_loop/README.md) | typed `@tool` functions + a system prompt |
| working code you want reachable as an agent | **Custom code** | [`custom/`](custom/README.md) | a thin `AgentHandler` adapter |

Each folder has its own `README.md` with the full walkthrough for that path. When
your agent is ready, [`HACKATHON_CHEATSHEET.md`](HACKATHON_CHEATSHEET.md) covers what
to include (README, dependencies, secrets) and how to hand it over.

---

## Install

The import package is `agent_skeleton`; this folder is `agent-skeleton`. Install it
editable so the import name resolves:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

The tool-loop **engine** and the `serve check` command run on the standard library
alone — you can validate an agent without installing anything. `a2a-sdk` + `uvicorn`
(pulled by `pip install -e .`) are only needed to actually **serve**.

---

## The three options at a glance

### 1. Wrap an endpoint → [`endpoint_wrapper/`](endpoint_wrapper/README.md)

You already have a running web service; you just want it reachable as a conversational
agent. Point an LLM loop at its URL and write **no code** — the model turns each
request into a call and reads the reply.

```bash
python -m agent_skeleton.endpoint_wrapper --card my.card.json \
    --endpoint-url https://api.example.com/run --endpoint-auth-env MY_API_TOKEN
```

### 2. LLM tool loop → [`tool_loop/`](tool_loop/README.md)

Best when the agent's value is *reasoning*: deciding which tool to call, chaining
calls, synthesizing an answer. You edit two files and the frozen engine runs the loop:

- [`tool_loop/tools.py`](tool_loop/tools.py) — your tools, as typed `@tool` functions
  inside `build_tools(config)`; the schema the model sees is **derived** from each
  function, so it can never drift from the code.
- [`tool_loop/prompt.py`](tool_loop/prompt.py) — `SYSTEM_PROMPT` + `normalize_result()`.

```bash
python -m agent_skeleton.serve check       # validate schemas <-> functions (no deps, no LLM)
python -m agent_skeleton.serve serve-a2a   # run the agent over A2A (needs a2a-sdk + uvicorn)
```

(You can also let the **registration service** generate this infrastructure for you —
you supply only the tool bodies, schemas, and prompt. See `tool_loop/README.md`.)

### 3. Custom code → [`custom/`](custom/README.md)

You already have working code; you don't rewrite it — you add a thin adapter that
subclasses `AgentHandler` and implements one method:

```python
from agent_skeleton import AgentHandler, FileInput

class MyHandler(AgentHandler):
    async def handle_structured(self, user_input, files=[], context=None) -> dict:
        # ... call your real code ...
        return {"answer": "the human-readable reply"}   # "answer" is REQUIRED
```

```bash
python -m agent_skeleton.serve serve-handler --file handler.py --class MyHandler --port 9110
```

See [`custom/INTEGRATION_GUIDE.md`](custom/INTEGRATION_GUIDE.md) for the full
walkthrough (the six questions to answer about your code, dependencies, credentials,
and a worked example).

---

## Repository map

```
agent_skeleton/
├── README.md            ← you are here (pick a path)
├── CLAUDE.md            ← working notes for editing inside the template
├── agent.card.json      ← WRITE: your agent's name, url, and skills (shared identity)
├── serve.py             ← entry-point shim (`python -m agent_skeleton.serve …`)
├── core/                ← the frozen engine — shared, rarely edited
├── endpoint_wrapper/    ← OPTION 1: wrap an existing HTTP/API endpoint
├── tool_loop/           ← OPTION 2: an LLM tool loop you fill in (tools.py + prompt.py)
└── custom/              ← OPTION 3: wrap your own code (AgentHandler + INTEGRATION_GUIDE)
```

**`core/` — the frozen plumbing** (copy, rarely edit):

| File | Role |
|---|---|
| `core/tool_engine.py` | `@tool` + `collect_tools` — derive a tool's schema from its typed function |
| `core/llm_loop.py` | the generic Chat-Completions tool loop (`run_tool_loop`, `run_agent`) |
| `core/spec.py` | `AgentSpec` — prompt + tools as data; one engine serves many agents |
| `core/executor.py` | `SkeletonAgentExecutor` — the A2A boundary for spec-driven agents |
| `core/serve.py` | `create_app` + `check` / `serve-a2a` / `serve-handler` CLI |
| `core/a2a_runtime.py` | a2a-sdk import guard + `data_part`/`text_part`/`task_updater` |
| `core/config.py` | identity, networking, model defaults + env readers |

The path folders import *from* `core/`, never the other way around at load time — so
`core/` stays a clean, self-contained base you can unit-test with no network.

---

## How it works (concepts shared by all three)

- **Stateless tool loop.** Chat Completions has no server-side memory, so the loop
  holds the whole `messages` history locally and resends it each step, appending the
  assistant's tool-call message *before* the tool results. Tool calls are read from
  the model's typed `tool_calls` field — never regex-parsed.
- **Dual-channel response.** Every reply carries a machine-readable `DataPart`
  (structured output the planner reads) *and* a human-readable text message.
- **Schemas are derived, not hand-written.** `@tool` builds each tool's schema from
  its function signature, so schema and code can't disagree. `serve check`
  (`tool_loop.tools.validate_tool_registry`) still validates any hand-written schemas
  (e.g. the endpoint-wrapper tools); a tool that declares `**kwargs` opts out.

---

## Testing

```bash
python -m agent_skeleton.serve check                        # schema/function alignment (stdlib only)
python -m pytest agent_skeleton/tests -q                    # engine + tool_loop tests
python -m pytest agent_skeleton/endpoint_wrapper/tests -q   # endpoint-wrapper tests
```

Because `core/a2a_runtime.py` degrades to a no-op when `a2a-sdk` is absent, you can
import the package, unit-test tool bodies, and run `serve check` without installing
the SDK; only serving requires it.

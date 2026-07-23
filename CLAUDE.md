# CLAUDE.md — agent_skeleton

Working notes for anyone (human or Claude) editing **inside this template**. For the
walkthrough see [`README.md`](README.md); each build option has its own deep dive in
its folder: [`tool_loop/README.md`](tool_loop/README.md),
[`custom/README.md`](custom/README.md) (+ [`custom/INTEGRATION_GUIDE.md`](custom/INTEGRATION_GUIDE.md)),
and [`endpoint_wrapper/README.md`](endpoint_wrapper/README.md).

---

## 1. What this is

A small, self-contained template for building an **A2A agent**. It isolates the
~70% of every agent that is plumbing into a "copy, don't edit" engine
([`core/`](core/)), and the ~30% that is the actual agent into **three
self-describing path folders**, all driven by that one frozen engine:

- [`endpoint_wrapper/`](endpoint_wrapper/) — **OPTION 1**: front an existing HTTP/API
  (or A2A) endpoint with an LLM loop; no code.
- [`tool_loop/`](tool_loop/) — **OPTION 2**: a hand-authored LLM tool loop; typed
  `@tool` functions in `tool_loop/tools.py` (+ `tool_loop/prompt.py`), run by
  `core.llm_loop.run_tool_loop`.
- [`custom/`](custom/) — **OPTION 3**: a custom handler; subclass `AgentHandler`
  (`custom/base.py`) and implement `handle_structured`, run by `HandlerExecutor`.

The dependency rule: the path folders import **from** `core/`, never the reverse at
module load. `core/` reaches into a path folder only through **lazy** (in-function)
imports — the demo default spec and the `serve check` validator pull `tool_loop`
lazily; the `serve-handler` command pulls `custom` lazily. So `agent_skeleton.core`
always imports on its own.

## 2. The two contracts

| Contract | Role | Here |
|---|---|---|
| **Agent Card** (`agent.card.json`) | identity + skills + endpoint | `a2a-sdk` `AgentCard` model, loaded by `core.serve.load_agent_card` |
| **A2A** | the actual call (HTTP/JSON-RPC) | `SkeletonAgentExecutor.execute()` (options 1–2) / `HandlerExecutor.execute()` (option 3) |

(Publishing a card into a directory so a planner can *discover* it is a deployment
concern, out of scope for this template.)

## 3. File map — where to edit, where not to

**`core/` — the frozen engine (copy; rarely edit):**

| File | Notes |
|---|---|
| `core/tool_engine.py` | `@tool` + `collect_tools`: derive schemas from typed functions |
| `core/llm_loop.py` | generic loop; `run_agent()` wires prompt/tools/dispatch |
| `core/spec.py` | `AgentSpec` seam (prompt+tools as data) + `default_demo_spec` + `llm_wrapper_spec` |
| `core/executor.py` | `SkeletonAgentExecutor.execute()` + A2A I/O (options 1–2) |
| `core/serve.py` | `create_app`, CLI (`check` / `serve-a2a` / `serve-handler`) |
| `core/a2a_runtime.py` | SDK import guard + `data_part`/`text_part`/`task_updater` |
| `core/config.py` | identity/networking/model defaults + env readers |

**`tool_loop/` — OPTION 2 (LLM tool loop):**

| File | Status | Notes |
|---|---|---|
| `tool_loop/tools.py` | **WRITE** | your tools as typed `@tool` functions inside `build_tools(config)` (schema derived); `validate_tool_registry()` |
| `tool_loop/prompt.py` | **WRITE** | `SYSTEM_PROMPT` + `normalize_result()` |
| `tool_loop/system_tools/` | copy | preset-tool catalog (`calculator`, `current_time`) armable by name |

**`custom/` — OPTION 3 (custom handler):**

| File | Status | Notes |
|---|---|---|
| `custom/base.py` | copy | `AgentHandler` (subclass + `handle_structured()`) + `FileInput` |
| `custom/handler_executor.py` | copy | `HandlerExecutor` — wraps any `AgentHandler` in A2A (heartbeat, runtime cap, credential context) |
| `custom/INTEGRATION_GUIDE.md` | docs | the OPTION 3 deep dive |

**`endpoint_wrapper/` — OPTION 1:** self-contained (code, tests, docs); see its README.

**Shared, at the package root:** `agent.card.json` (**WRITE**: skills, url, version),
`serve.py` (entry-point shim that forwards `python -m agent_skeleton.serve …` to
`core.serve`), `__init__.py` (re-exports the public API).

**Separation of concerns to preserve:** `core/executor.py` / `custom/handler_executor.py`
are the *only* files that know about A2A; `core/llm_loop.py` + `tool_loop/tools.py` +
`tool_loop/prompt.py` are the engine/agent and know nothing about A2A. Keep it that
way — it's what lets you unit-test the engine and run `serve check` with no network
and no `a2a-sdk` installed.

## 4. How to add a tool (OPTION 2 / tool_loop)

1. Write a typed function decorated with `@tool` INSIDE `build_tools(config)` in
   `tool_loop/tools.py`; annotate its params (use `Annotated[T, "description"]` to
   document one) and give it a docstring. Add it to the list `build_tools` returns.
2. The schema is derived from the signature — there is nothing else to write.
   `@tool` turns the typed function into the tool the LLM sees (see §5).
3. To bake config/auth, read it from `config` inside the tool — it's captured by the
   closure and never exposed to the model. Put fixed configuration in `CONFIG`.
4. `python -m agent_skeleton.serve check` — confirms everything still aligns.

## 5. Schemas are derived (drift is impossible)

`@tool` (in `core/tool_engine.py`) derives each tool's schema from its typed
signature + docstring, so there is ONE source of truth and the schema cannot disagree
with the function. `validate_tool_registry()` (in `tool_loop/tools.py`) remains as a
safety net for any HAND-WRITTEN schemas (e.g. the endpoint-wrapper tools, or a
registry assembled by hand); it runs in `create_app()` and as `serve check`, and for
`@tool` tools it always passes. A tool that declares `**kwargs` opts out of the strict
parameter check.

## 6. Gotchas

- **Dummy key guard:** `OPENAI_API_KEY` must be non-empty even for vLLM; set a
  placeholder.
- **vLLM tool calling needs launch flags:** `--enable-auto-tool-choice
  --tool-call-parser <parser>`, or the model silently stops calling tools.
- **Model-name matching:** raw OpenAI clients send the model string verbatim; it must
  equal vLLM's `--served-model-name`.
- **Step cap:** the loop is bounded by `MAX_TOOL_STEPS` (`core/config.py`); a task
  needing more rounds is truncated.
- **Blocking handlers (option 3):** a blocking call freezes the heartbeat — wrap it in
  `await asyncio.to_thread(...)`.
- **No auth:** the served app binds `0.0.0.0` with empty `securitySchemes` — fine for
  local dev, not for exposure.
- **Import name:** the folder is `agent-skeleton`, the package is `agent_skeleton`;
  `pip install -e .` (package-dir maps `agent_skeleton` to `.`) so imports resolve.
  Every subpackage (`core`, `tool_loop`, `tool_loop.system_tools`, `custom`,
  `endpoint_wrapper`) is listed in `pyproject.toml` — add new ones there.
- **The `serve.py` shim:** the real CLI/app-factory lives in `core/serve.py`; the
  root `serve.py` just forwards so `python -m agent_skeleton.serve …` keeps working
  (and `from agent_skeleton.serve import create_app` still resolves).

## 7. Testing

```bash
python -m agent_skeleton.serve check                        # schema/function alignment (stdlib only)
python -m pytest agent_skeleton/tests -q                    # engine + tool_loop tests
python -m pytest agent_skeleton/endpoint_wrapper/tests -q   # endpoint-wrapper feature
python -m compileall -q agent_skeleton                          # syntax (recurses)
```

Because `core/a2a_runtime.py` degrades gracefully when `a2a-sdk` is missing (the
executor base class becomes `object`), you can import and test the engine and the
alignment check without the SDK; only *serving* requires it.

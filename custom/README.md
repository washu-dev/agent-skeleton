# OPTION 3 — wrap your own code

This is the path when you **already have working code** — it reads a PDF, calls an
API, crunches data, runs its own LLM loop — and you just want it reachable as an
agent. You do **not** rewrite it. You add one thin adapter and the framework wraps it
in a web server.

Use this path when you have *code* (a function, a class, a package). If you have a
running *service* to expose, use [`../endpoint_wrapper/`](../endpoint_wrapper/README.md);
if the task is best solved by an LLM calling tools you author, use
[`../tool_loop/`](../tool_loop/README.md).

## The contract

Add a class that subclasses `AgentHandler` (from [`base.py`](base.py)) and implements
one async method that returns a dict containing an `"answer"`:

```python
from agent_skeleton import AgentHandler, FileInput

class MyHandler(AgentHandler):
    async def handle_structured(
        self,
        user_input: str,                 # the caller's text
        files: list[FileInput] = [],     # attached files (.bytes, .name, .as_tempfile())
        context: dict | None = None,     # optional: per-user credentials (declare to receive)
    ) -> dict:
        # ... call your real code ...
        return {"answer": "the human-readable reply"}   # "answer" is REQUIRED
```

- `user_input` is the caller's text; `files` are attached files; declare a `context`
  parameter to receive per-user credentials (`context["credentials"]`).
- If your code is blocking, wrap it in `await asyncio.to_thread(...)` so the heartbeat
  keeps flowing.

The framework gives you, for free: A2A request parsing, base64 file decoding into
`FileInput`, a heartbeat (so long calls don't time out), a runtime cap, credential
injection, error handling, and the dual machine+human response.

## Run it locally

```bash
python -m agent_skeleton.serve serve-handler --file handler.py --class MyHandler --port 9110
```

## Full walkthrough

[`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) is the deep dive: the **six questions**
to answer about your code (entry point, input mapping, output→answer, sync/async,
credentials, dependencies), how to package a single file or a zip, how credentials and
system packages work, the exact-error troubleshooting table, and a complete worked
example (a paper reviewer). Read it before you hand your agent over.

## What's in this folder

| File | Role |
|---|---|
| [`base.py`](base.py) | `AgentHandler` (the contract you subclass) + `FileInput` |
| [`handler_executor.py`](handler_executor.py) | `HandlerExecutor` — wraps any `AgentHandler` for A2A (heartbeat, runtime cap, credential context) |
| [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) | the full walkthrough |

`base.py` and `handler_executor.py` are frozen plumbing — you write only your own
`handler.py` (kept wherever your code lives, not in this folder).

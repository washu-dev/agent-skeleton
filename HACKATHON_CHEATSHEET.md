# Submitting an agent

This mirrors the "what to build / what to include / how you're done" part of the
walkthrough. You build your agent one of three ways, test it locally, then hand it over
with a few required files. You write no server, protocol, or discovery code — that's
generated for you.

## 1. Pick a path and build it

Each path is a self-describing folder (see [README.md](README.md) for the overview):

- **Option 1 — wrap an endpoint.** Point an LLM loop at a running HTTP/API service;
  write no code. See [endpoint_wrapper/README.md](endpoint_wrapper/README.md).
- **Option 2 — an LLM tool loop.** Write typed `@tool` functions in
  `tool_loop/tools.py`, plus `tool_loop/prompt.py` and `agent.card.json`. See
  [tool_loop/README.md](tool_loop/README.md).
- **Option 3 — wrap your own code.** Add a small `handler.py` that subclasses
  `AgentHandler`. See [custom/INTEGRATION_GUIDE.md](custom/INTEGRATION_GUIDE.md).

## 2. Test it locally (this is how you know you're done)

Run it until it returns the expected output — locally, before handing it over.

```bash
# Option 1 (wrap an endpoint):
python -m agent_skeleton.endpoint_wrapper --card my.card.json \
    --endpoint-url https://api.example.com/run

# Option 2 (LLM tool loop):
python -m agent_skeleton.serve check        # schemas <-> functions align (no LLM, no deps)
python -m agent_skeleton.serve serve-a2a    # run the agent

# Option 3 (custom code):
python -m agent_skeleton.serve serve-handler --file handler.py --class MyHandler --port 9110
```

**Definition of done:** it runs locally and produces its final answer — a dict with an
`"answer"` (Options 1 & 3) or the model's answer produced through the loop (Option 2).

## 3. What to include when you hand it over

**A `README.md`** with:
- a plain-language description of what the agent does;
- its explicit **input/output** (what it takes, what it returns);
- the **entry-point file and class name** (for Option 3), the fact that it's a
  tool-loop agent (Option 2), or the wrapped endpoint URL + protocol (Option 1).

**Your dependencies**, in three kinds — the second is the one that silently breaks:

| Kind | How to declare |
|---|---|
| Python packages | `requirements.txt` or a `pyproject.toml` |
| **System binaries** (pip can't install these) | list them explicitly, e.g. `tesseract-ocr`, `ffmpeg`, `poppler-utils` — only you know your code needs them |
| Hardware | note any GPU / large-RAM needs |

**Your secrets, handled safely:**
- Reference each secret by an **environment-variable name**; leave the actual values
  (and any `.env` / config file) out of what you send.
- For per-user keys, read them from `context["credentials"]` in your handler (Option 3) —
  never hard-code a key. This lets each user slot in their own.

## 4. If your agent calls an LLM

- We're working on providing a shared endpoint; in the meantime use a free option or
  tunnel into a RIS compute node.
- Prefer **stateless** calls (the OpenAI Chat Completions standard) — that's what the
  template's loop uses, so the same code works against hosted OpenAI or a self-hosted
  vLLM endpoint (set `OPENAI_BASE_URL`).

## 5. Send it

Share a repo with us! 

> **Submit to:** https://docs.google.com/forms/d/e/1FAIpQLSeBv441FBw2vYyUqdW5Geimq0rxFJW2g0meAIofUOqEW1GgsA/viewform **by:** Wednesday 6:00pm 

## Checklist

- [ ] Built as Option 1 (endpoint URL, no code), Option 2 (`@tool` functions in `tool_loop/tools.py` + prompt), or Option 3 (`handler.py` + your code).
- [ ] Runs locally and returns `{"answer": ...}` / a final answer.
- [ ] `README.md` with description, explicit I/O, and entry-point file + class.
- [ ] Dependencies listed — pip packages **and** any system binaries **and** hardware.
- [ ] Secrets referenced by env-var name; no keys or config files included.
- [ ] (Option 2) `python -m agent_skeleton.serve check` passes.

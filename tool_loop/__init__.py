"""agent_skeleton.tool_loop — OPTION 2: an LLM tool loop you fill in.

You supply a system prompt and a set of typed tools; the frozen engine in
``agent_skeleton.core`` runs the model-calls-tools loop. Best when the agent's value
is reasoning: deciding which tool to call, chaining calls, synthesizing an answer.

The two files you WRITE:
    tools.py    — your tools, as typed ``@tool`` functions inside ``build_tools(config)``
                  (the JSON schema the model sees is DERIVED from each function)
    prompt.py   — ``SYSTEM_PROMPT`` + ``normalize_result()`` (the stable output shape)

Plus:
    system_tools/  — a catalog of ready-made preset tools you can arm a wrapper with
                     by name (see ``agent_skeleton.llm_wrapper_spec``).

See tool_loop/README.md for the full walkthrough.
"""

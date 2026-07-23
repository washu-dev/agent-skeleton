"""agent_skeleton.core — the frozen engine shared by all three build options.

This is the ~70% plumbing you copy but rarely edit. Nothing here is specific to one
build path; the path folders (endpoint_wrapper/, tool_loop/, custom/) import from
here, never the other way around at load time.

  a2a_runtime  — a2a-sdk import guard + data_part/text_part/task_updater wrappers
  config       — identity, networking, model defaults + env readers
  tool_engine  — @tool / collect_tools: derive a tool's JSON schema from a typed fn
  llm_loop     — the generic Chat-Completions tool loop (run_tool_loop / run_agent)
  spec         — AgentSpec (prompt + tools as data) so one engine serves many agents
  executor     — SkeletonAgentExecutor: the A2A boundary for spec-driven agents
  serve        — create_app + the `check` / `serve-a2a` / `serve-handler` CLI

The convenient public names are re-exported from the top-level ``agent_skeleton``
package; import them from there (``from agent_skeleton import AgentSpec, tool``).
"""

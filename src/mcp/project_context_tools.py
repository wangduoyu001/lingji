from __future__ import annotations


def register_project_context_tools(mcp, project_context_service, default_agent_resolver):
    async def lingji_build_context(project_id: str, task: str, session_id: str = "", max_chars: int | None = None):
        resolved = default_agent_resolver() if callable(default_agent_resolver) else "codex"
        agent_id = "codex" if str(resolved or "codex").lower() == "codex" else "codex"
        return project_context_service.build(agent_id=agent_id, project_id=project_id, query=task, session_id=session_id, max_chars=max_chars, allow_cross_project=False)

    decorator = getattr(mcp, "tool", None)
    if callable(decorator):
        registered = decorator(name="lingji_build_context")(lingji_build_context)
        return registered
    register = getattr(mcp, "register_tool", None)
    if callable(register):
        register("lingji_build_context", lingji_build_context)
    return lingji_build_context

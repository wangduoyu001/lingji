from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

READ_TOOLS = (
    "search_memory",
    "fetch_memory",
    "get_core_memory",
    "build_context_pack",
    "recent_changes",
    "memory_health",
)
PROPOSAL_TOOLS = (*READ_TOOLS, "propose_memory")


@dataclass(frozen=True)
class AIClientProfile:
    agent_id: str
    display_name: str
    transport: str
    allowed_tools: tuple[str, ...]
    allowed_privacy: tuple[str, ...]
    max_context_chars: int
    can_propose_memory: bool = True
    can_modify_core_memory: bool = False
    local_only: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AIProfileRegistry:
    """Provider-neutral permissions for AI clients connecting to LingJi."""

    def __init__(self, profiles: Iterable[AIClientProfile] | None = None):
        self._profiles = {profile.agent_id: profile for profile in (profiles or self.defaults())}

    @staticmethod
    def defaults() -> tuple[AIClientProfile, ...]:
        remote_privacy = ("public", "private")
        local_privacy = ("public", "private", "restricted")
        return (
            AIClientProfile("chatgpt", "ChatGPT", "mcp_streamable_http", PROPOSAL_TOOLS, remote_privacy, 14000),
            AIClientProfile("codex", "Codex", "mcp_stdio", PROPOSAL_TOOLS, remote_privacy, 18000),
            AIClientProfile("claude", "Claude", "mcp_streamable_http", PROPOSAL_TOOLS, remote_privacy, 16000),
            AIClientProfile("gemini", "Gemini", "mcp_streamable_http", PROPOSAL_TOOLS, remote_privacy, 14000),
            AIClientProfile("kimi", "Kimi", "mcp_stdio", PROPOSAL_TOOLS, remote_privacy, 14000),
            AIClientProfile("deepseek", "DeepSeek", "mcp_stdio", PROPOSAL_TOOLS, remote_privacy, 14000),
            AIClientProfile(
                "ollama",
                "Ollama Local",
                "mcp_stdio",
                PROPOSAL_TOOLS,
                local_privacy,
                20000,
                local_only=True,
            ),
            AIClientProfile(
                "lingji-local",
                "LingJi Local Agent",
                "internal",
                PROPOSAL_TOOLS,
                local_privacy,
                24000,
                local_only=True,
            ),
        )

    def get(self, agent_id: str) -> AIClientProfile:
        key = str(agent_id or "").strip().lower()
        if key not in self._profiles:
            raise KeyError(f"Unknown AI client profile: {agent_id}")
        return self._profiles[key]

    def register(self, profile: AIClientProfile) -> None:
        self._profiles[profile.agent_id] = profile

    def list(self) -> list[dict[str, object]]:
        return [profile.to_dict() for profile in sorted(self._profiles.values(), key=lambda item: item.agent_id)]

    def require_tool(self, agent_id: str, tool_name: str) -> AIClientProfile:
        profile = self.get(agent_id)
        if tool_name not in profile.allowed_tools:
            raise PermissionError(f"{profile.display_name} is not allowed to use {tool_name}")
        return profile

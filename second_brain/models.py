from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message_id: str | None = None
    role: str
    content: str
    timestamp: str | None = None


class ConversationInput(BaseModel):
    conversation_id: str | None = None
    source: str = "ai_chat"
    title: str = "Untitled conversation"
    project: str = "global"
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[ChatMessage]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    path: str | None = None
    conversation: ConversationInput | None = None
    distill: bool = True


class SearchRequest(BaseModel):
    query: str
    project: str | None = None
    memory_types: list[str] = Field(default_factory=list)
    active_only: bool = True
    top_k: int = Field(default=10, ge=1, le=50)
    include_knowledge: bool = True


class ContextRequest(BaseModel):
    agent: str = "codex"
    project: str = "global"
    repository: str | None = None
    task: str
    max_tokens: int = Field(default=6000, ge=500, le=30000)


class DistillRequest(BaseModel):
    conversation_id: str | None = None
    source_id: str | None = None


class ReviewRequest(BaseModel):
    memory_id: str
    reason: str | None = None


class SupersedeRequest(BaseModel):
    old_memory_id: str
    new_memory_id: str | None = None
    new_memory: dict[str, Any] | None = None
    reason: str = "Newer confirmed memory"


class CodexTaskRequest(BaseModel):
    task_id: str | None = None
    project: str = "global"
    request: str
    status: Literal["pending", "running", "success", "failed", "partial"] = "success"
    result: str | None = None
    files_changed: list[str] = Field(default_factory=list)
    tests: list[dict[str, Any] | str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)
    commit_hash: str | None = None


class KnowledgeIndexRequest(BaseModel):
    path: str

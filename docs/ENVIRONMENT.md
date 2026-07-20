# ENVIRONMENT.md — LingJi Environment Setup

> Generated: 2026-07-20

## Development Machine

| Attribute | Value |
|-----------|-------|
| OS | Windows |
| Python | 3.10+ (virtual env at .venv/) |
| GPU | RTX 4060 Ti (8GB) |
| Ollama | Running at http://127.0.0.1:11434 |
| Obsidian | Installed (native CLI at Obsidian.com) |

## Virtual Environment

`powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
`

## Dependency Files

| File | Purpose | Key Packages |
|------|---------|--------------|
| requirements.txt | Base | pydantic-settings, requests |
| requirements-second-brain.txt | Second brain API | fastapi, uvicorn, pydantic, qdrant-client |
| requirements-desktop.txt | Desktop client | PySide6 |

## Ollama Models

| Model | Purpose | Status |
|-------|---------|--------|
| nomic-embed-text | Fallback embedding | Installed |
| bge-m3 | Primary embedding | Pending installation |
| qwen3:8b | Fallback LLM | Available |

## DeepSeek

API key stored in .env file for PEMIS v6 LLM access.
The second brain does not directly use DeepSeek; it uses Ollama for embeddings.

## OBSOLETE (from original PEMIS v4)

The original project references Qdrant Docker service on port 6333. In this worktree,
embedded Qdrant (file-based or :memory:) replaces Docker entirely.

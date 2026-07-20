# GETTING_STARTED.md — LingJi (灵机) Quick Start

> Generated: 2026-07-20

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Virtual environment at .venv/ |
| Ollama | Any | Local LLM server at 127.0.0.1:11434 |
| Obsidian | Any | For vault access (optional for second brain) |
| Git | Any | For repository management |
| DeepSeek API key | — | For PEMIS v6 LLM (in .env) |

## Installation

### 1. Clone the repository (if not already)

`powershell
git clone https://github.com/wangduoyu001/lingji.git D:\codex\lingji-second-brain
cd D:\codex\lingji-second-brain
git checkout feature/second-brain-memory
`

### 2. Set up Python virtual environment

`powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
`

### 3. Install dependencies

`powershell
# Base dependencies
pip install -r requirements.txt

# Second brain dependencies
pip install -r requirements-second-brain.txt

# Desktop dependencies (optional)
pip install -r requirements-desktop.txt
`

### 4. Configure environment variables

`powershell
cp .env.second-brain.example .env.second-brain
# Edit .env.second-brain with your paths
# For PEMIS v6: create .env with DEEPSEEK_API_KEY
`

### 5. Pull Ollama models

`powershell
ollama pull nomic-embed-text
# Optional: ollama pull qwen3:8b
# Optional: ollama pull bge-m3
`

## Starting the System

### PEMIS v6 (Original Service)

Run in the **original project directory** (C:\\Users\\Administrator\\Documents\\New project-ai):

`powershell
python run_service.py
`

### Second Brain Service (Parallel Upgrade)

From this worktree:

`powershell
# Start all (API + watcher if defaults enabled)
powershell -ExecutionPolicy Bypass -File .\\scripts\\second_brain\\start.ps1

# Or individually:
powershell -ExecutionPolicy Bypass -File .\\scripts\\second_brain\\start-api.ps1
powershell -ExecutionPolicy Bypass -File .\\scripts\\second_brain\\start-watcher.ps1
`

### Desktop Client

`powershell
# First-time setup
powershell -ExecutionPolicy Bypass -File .\\scripts\\desktop\\setup.ps1

# Launch
powershell -ExecutionPolicy Bypass -File .\\scripts\\desktop\\start-desktop.ps1
`

Or double-click the **灵机第二大脑** desktop shortcut.

## Health Check

`powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\second_brain\\health.ps1
# Or: curl http://127.0.0.1:8765/health
`

## Running Tests

`powershell
.venv\\Scripts\\Activate.ps1
python -m pytest tests/ -v
`

## Stopping

`powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\second_brain\\stop.ps1
`

## Rollback

1. Stop the second-brain service
2. Delete this worktree (after preserving any wanted data from data/ directory)
3. Original LingJi at C:\\...\\New project-ai is untouched

Pre-upgrade backup: D:\\codex\\backups\\lingji-second-brain\\20260715-225503

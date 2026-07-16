# Recent Decisions

- Use a D-drive Git worktree on `feature/second-brain-memory` instead of changing `master`.
- Use SQLite as structured truth and embedded Qdrant as a rebuildable local vector cache.
- Prefer `bge-m3` through Ollama and fall back to the already installed `nomic-embed-text`.
- Keep the listener independent from both the original LingJi startup chain and the second-brain API process.
## 2026-07-16

- Use PySide6 only; do not add a web UI, Electron, WebView, HTML, CSS, or JS.
- Keep API running when the UI closes by default; keep watcher disabled by default.
- Desktop defaults to acceptance; headerless API traffic remains production.
- Dependencies and pip cache remain on D: in the project venv and D:\codex\cache\pip.

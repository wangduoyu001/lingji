# Recent Decisions

- Use a D-drive Git worktree on `feature/second-brain-memory` instead of changing `master`.
- Use SQLite as structured truth and embedded Qdrant as a rebuildable local vector cache.
- Prefer `bge-m3` through Ollama and fall back to the already installed `nomic-embed-text`.
- Keep the listener independent from both the original LingJi startup chain and the second-brain API process.

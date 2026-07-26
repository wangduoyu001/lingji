# AI_MODEL_STRATEGY.md — LingJi AI Model Strategy

> Generated: 2026-07-20

## Tiered Model Architecture

LingJi uses a tiered approach for AI models, with automatic fallback:

### PEMIS v6 (Background Scheduler)

| Role | Primary | Fallback | Purpose |
|------|---------|----------|---------|
| LLM | deepseek-chat (DeepSeek API) | qwen3:8b (Ollama) | Opportunity analysis, decisions, capture |
| Embedding | nomic-embed-text (Ollama) | (none) | Contextual indexing (currently unused in PEMIS) |

The DeepSeek API key is stored in .env. When unavailable, PEMIS falls back to local Ollama.

### Second Brain (Memory & Knowledge)

| Role | Primary | Fallback | Purpose |
|------|---------|----------|---------|
| Embedding | bge-m3 (Ollama) | nomic-embed-text (Ollama) | Memory and knowledge vectorization |
| LLM | None | None | Second brain does not use LLM directly |

BGE-M3 is preferred for its multilingual support. If not installed in Ollama,
the fallback 
omic-embed-text is used automatically.

## Fallback Logic

`python
# Second brain embedder fallback chain (embedding.py):
ordered = (self.active_model, self.model, self.fallback_model)
for model in dict.fromkeys(ordered):
    if not model or model in self._unavailable:
        continue
    # Try embedding, fall through on failure
`

## Configuration

Change models via environment variables:

`powershell
# PEMIS v6
LLM_MODEL=qwen3:8b
FALLBACK_LLM=qwen3:8b

# Second brain
SECOND_BRAIN_EMBED_MODEL=bge-m3
SECOND_BRAIN_FALLBACK_EMBED_MODEL=nomic-embed-text
`

## Notes

- The second brain does not use any LLM for memory generation — it relies on structure and embedding.
- Distillation uses content hashing and structure, not AI generation.
- The original PEMIS v4 (upstream master) references deepseek-chat for LLM analysis.

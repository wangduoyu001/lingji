from __future__ import annotations

from dataclasses import dataclass

from second_brain.config import Settings, settings
from second_brain.conflict.service import ConflictService
from second_brain.connectors.chat import ChatConnector
from second_brain.connectors.codex import CodexConnector
from second_brain.connectors.obsidian import ObsidianConnector
from second_brain.db import Database
from second_brain.distillation.service import DistillationService
from second_brain.embedding import OllamaEmbedder
from second_brain.memory.service import MemoryService
from second_brain.retrieval.service import RetrievalService
from second_brain.vector_store import VectorStore


@dataclass
class Runtime:
    settings: Settings
    database: Database
    embedder: OllamaEmbedder
    vectors: VectorStore
    memories: MemoryService
    retrieval: RetrievalService
    distillation: DistillationService
    conflicts: ConflictService
    chats: ChatConnector
    codex: CodexConnector
    obsidian: ObsidianConnector

    def close(self) -> None:
        self.vectors.close()


def build_runtime(config: Settings = settings) -> Runtime:
    config.ensure_directories()
    database = Database(config.database_path)
    database.initialize()
    embedder = OllamaEmbedder(config.ollama_url, config.embed_model, config.fallback_embed_model)
    vectors = VectorStore(config.qdrant_collection, path=config.qdrant_path, url=config.qdrant_url)
    memories = MemoryService(database, embedder, vectors)
    return Runtime(
        settings=config,
        database=database,
        embedder=embedder,
        vectors=vectors,
        memories=memories,
        retrieval=RetrievalService(database, embedder, vectors),
        distillation=DistillationService(database, memories),
        conflicts=ConflictService(database),
        chats=ChatConnector(database, memories, config),
        codex=CodexConnector(database, memories),
        obsidian=ObsidianConnector(database, memories, embedder, vectors, config.obsidian_knowledge_dir),
    )

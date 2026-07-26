from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from src.retrieval.index_coordinator import MemoryIndexCoordinator
from src.retrieval.memory_db import MemoryDatabase


class FakeSemanticProvider:
    def __init__(self):
        self.points = {}
        self.upsert_batches = []
        self.deleted = []
        self.fail_upsert = False
        self.fail_delete = False

    def upsert(self, point):
        return self.upsert_many([point])[0]

    def upsert_many(self, points):
        selected = list(points)
        self.upsert_batches.append(selected)
        if self.fail_upsert:
            raise RuntimeError("semantic backend unavailable")
        ids = []
        for point in selected:
            self.points[point.chunk_id] = point
            ids.append(f"point:{point.chunk_id}")
        return ids

    def delete(self, chunk_id):
        self.deleted.append(chunk_id)
        if self.fail_delete:
            raise RuntimeError("semantic delete unavailable")
        self.points.pop(chunk_id, None)

    def delete_memory(self, memory_id):
        for chunk_id, point in list(self.points.items()):
            if point.memory_id == memory_id:
                self.delete(chunk_id)


class FakeStateDatabase:
    def __init__(self):
        self.events = []

    def append_event(self, event_type, entity_type, entity_id, payload):
        self.events.append((event_type, entity_type, entity_id, payload))


class MemoryIndexCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.vault.mkdir(parents=True)
        self.database = MemoryDatabase(root / "storage" / "memory.db")
        self.semantic = FakeSemanticProvider()
        self.state_db = FakeStateDatabase()
        self.coordinator = MemoryIndexCoordinator(
            self.database,
            self.semantic,
            state_db=self.state_db,
            semantic_batch_size=2,
        )

    def _entry(
        self,
        relative_path: str,
        memory_id: str,
        body: str,
        *,
        title: str = "Test memory",
        tags=None,
        privacy: str = "private",
    ):
        tags = list(tags or ["memory"])
        path = self.vault / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = (
            "---\n"
            f"id: {memory_id}\n"
            f"privacy: {privacy}\n"
            f"tags: [{', '.join(tags)}]\n"
            "---\n"
        )
        text = frontmatter + body
        path.write_text(text, encoding="utf-8")
        return {
            "id": memory_id,
            "relative_path": relative_path,
            "title": title,
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "review_status": "approved",
            "privacy": privacy,
            "importance": "medium",
            "project": ["lingji"],
            "tags": tags,
            "agent_scope": ["all"],
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def test_initial_sync_upserts_all_lexical_chunks(self):
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")

        result = self.coordinator.sync([entry], self.vault)

        self.assertEqual(result["added"], 1)
        self.assertEqual(result["semantic"]["status"], "healthy")
        self.assertGreater(result["semantic"]["upserted"], 0)
        memory = self.database.fetch_memory("MEM-FIRST", include_chunks=True)
        self.assertIsNotNone(memory)
        self.assertEqual(len(self.semantic.points), len(memory["chunks"]))
        indexed = next(iter(self.semantic.points.values()))
        self.assertEqual(indexed.payload["relative_path"], "03-Knowledge/first.md")
        self.assertNotEqual(indexed.text, "")

    def test_unchanged_sync_does_not_repeat_semantic_upsert(self):
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")
        self.coordinator.sync([entry], self.vault)
        previous_batches = len(self.semantic.upsert_batches)

        result = self.coordinator.sync([entry], self.vault)

        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["semantic"]["upserted"], 0)
        self.assertEqual(len(self.semantic.upsert_batches), previous_batches)

    def test_content_update_deletes_old_chunk_and_upserts_new_chunk(self):
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")
        self.coordinator.sync([entry], self.vault)
        old_ids = set(self.semantic.points)
        updated = self._entry(
            "03-Knowledge/first.md",
            "MEM-FIRST",
            "# 第一条\n\n正文已经发生变化。\n",
        )

        result = self.coordinator.sync([updated], self.vault)

        self.assertEqual(result["updated"], 1)
        self.assertGreater(result["semantic"]["upserted"], 0)
        self.assertTrue(old_ids.intersection(self.semantic.deleted))
        self.assertFalse(old_ids.intersection(self.semantic.points))

    def test_metadata_update_reupserts_stable_chunk_id(self):
        entry = self._entry(
            "03-Knowledge/first.md",
            "MEM-FIRST",
            "# 第一条\n\n正文保持不变。\n",
            tags=["old"],
        )
        self.coordinator.sync([entry], self.vault)
        old_ids = set(self.semantic.points)
        changed = self._entry(
            "03-Knowledge/first.md",
            "MEM-FIRST",
            "# 第一条\n\n正文保持不变。\n",
            tags=["new"],
        )

        result = self.coordinator.sync([changed], self.vault)

        self.assertEqual(set(self.semantic.points), old_ids)
        self.assertEqual(result["semantic"]["updated"], len(old_ids))
        point = self.semantic.points[next(iter(old_ids))]
        self.assertEqual(point.payload["tags"], ["new"])

    def test_removed_document_deletes_semantic_chunks(self):
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")
        self.coordinator.sync([entry], self.vault)
        chunk_ids = set(self.semantic.points)
        (self.vault / "03-Knowledge/first.md").unlink()

        result = self.coordinator.sync([], self.vault)

        self.assertEqual(result["removed"], 1)
        self.assertEqual(result["semantic"]["deleted"], len(chunk_ids))
        self.assertTrue(chunk_ids.issubset(set(self.semantic.deleted)))
        self.assertEqual(self.semantic.points, {})

    def test_semantic_failure_degrades_without_rolling_back_lexical_index(self):
        self.semantic.fail_upsert = True
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")

        result = self.coordinator.sync([entry], self.vault)

        self.assertTrue(result["degraded"])
        self.assertEqual(result["semantic"]["status"], "degraded")
        self.assertEqual(result["warnings"][0]["code"], "semantic_upsert_failed")
        self.assertIsNotNone(self.database.fetch_memory("MEM-FIRST"))
        self.assertEqual(self.state_db.events[-1][0], "memory_index_sync_degraded")

    def test_lexical_only_mode_remains_supported(self):
        entry = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")
        coordinator = MemoryIndexCoordinator(self.database, None)

        result = coordinator.sync([entry], self.vault)

        self.assertFalse(result["degraded"])
        self.assertEqual(result["semantic"]["status"], "disabled")
        self.assertIsNotNone(self.database.fetch_memory("MEM-FIRST"))

    def test_force_rebuild_reupserts_all_current_chunks(self):
        first = self._entry("03-Knowledge/first.md", "MEM-FIRST", "# 第一条\n\n正文一。\n")
        second = self._entry("03-Knowledge/second.md", "MEM-SECOND", "# 第二条\n\n正文二。\n")
        self.coordinator.sync([first, second], self.vault)
        expected = len(self.semantic.points)
        self.semantic.upsert_batches.clear()

        result = self.coordinator.sync([first, second], self.vault, force=True)

        self.assertTrue(result["full_rebuild"])
        self.assertEqual(result["semantic"]["upserted"], expected)
        self.assertGreater(len(self.semantic.upsert_batches), 0)


if __name__ == "__main__":
    unittest.main()

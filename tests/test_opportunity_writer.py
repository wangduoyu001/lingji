import tempfile
import unittest
from pathlib import Path

from src.opportunities import OpportunityCardWriter
from src.obsidian.frontmatter import split_frontmatter


class OpportunityCardWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.vault = base / "vault"
        self.output = base / "storage" / "opportunities"
        self.source = self.vault / "02-Sources" / "Documents" / "source.md"
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_text("# Source\n", encoding="utf-8")
        self.writer = OpportunityCardWriter(self.output, self.vault)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _analysis(self, title="同名机会"):
        return {
            "title": title,
            "summary": "这是一个足够长的机会摘要，用于说明目标用户、需求、执行条件和验证方式。" * 3,
            "how": "第一步验证，第二步制作，第三步发布，第四步复盘。" * 6,
            "direction": "服务",
            "difficulty": 2,
            "speed": "fast",
        }

    def test_stable_source_id_produces_stable_file_and_memory_id(self):
        first = self.writer.write(self.source, "LJ-SOURCE-1", "hash-a", self._analysis())
        second = self.writer.write(self.source, "LJ-SOURCE-1", "hash-b", self._analysis())
        self.assertEqual(first["file"], second["file"])
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(list(self.output.glob("*.md"))), 1)
        metadata, _ = split_frontmatter(Path(second["path"]).read_text(encoding="utf-8"))
        self.assertEqual(metadata["source_id"], "LJ-SOURCE-1")
        self.assertEqual(metadata["source_content_hash"], "hash-b")
        self.assertEqual(metadata["verification_status"], "unverified")

    def test_same_title_from_different_sources_does_not_collide(self):
        first = self.writer.write(self.source, "LJ-SOURCE-1", "hash-a", self._analysis())
        second = self.writer.write(self.source, "LJ-SOURCE-2", "hash-a", self._analysis())
        self.assertNotEqual(first["file"], second["file"])
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(list(self.output.glob("*.md"))), 2)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.user_feedback import UserFeedback


class FeedbackInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.settings = SimpleNamespace(
            storage_path=base / "storage",
            vault_path=base / "vault",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_feedback_is_read_from_owner_controlled_note(self):
        feedback = UserFeedback(self.settings)
        self.assertTrue(feedback.feedback_inbox.exists())
        text = feedback.feedback_inbox.read_text(encoding="utf-8")
        text = text.replace("- 喜欢/感兴趣: ", "- 喜欢/感兴趣: Obsidian Bases")
        feedback.feedback_inbox.write_text(text, encoding="utf-8")

        result = feedback.read_feedback_inbox()
        self.assertTrue(result["changed"])
        state = json.loads(feedback.feedback_path.read_text(encoding="utf-8"))
        self.assertEqual(state["liked"][-1]["content"], "Obsidian Bases")
        self.assertIn("Obsidian Bases", feedback.feedback_inbox.read_text(encoding="utf-8"))

    def test_same_feedback_is_not_duplicated_on_repeated_reads(self):
        feedback = UserFeedback(self.settings)
        text = feedback.feedback_inbox.read_text(encoding="utf-8")
        feedback.feedback_inbox.write_text(
            text.replace("- 我想到的新方向: ", "- 我想到的新方向: 建立实体关系中心"),
            encoding="utf-8",
        )
        feedback.read_feedback_inbox()
        feedback.read_feedback_inbox()
        state = feedback.get_preferences()
        self.assertEqual(len(state["new_ideas"]), 1)


if __name__ == "__main__":
    unittest.main()

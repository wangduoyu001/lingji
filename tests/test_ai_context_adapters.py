import unittest

from src.gateway import AIContextAdapter


class AIContextAdapterTests(unittest.TestCase):
    def setUp(self):
        self.pack = {
            "agent_id": "chatgpt",
            "memory_revision": 12,
            "project": "LingJi",
            "query": "继续开发",
            "markdown": "# LingJi Context Pack\n\n核心规则与检索结果。\n",
            "sections": [
                {
                    "citation": {
                        "memory_id": "LJ-MEM-1",
                        "path": "03-Knowledge/Core-Memory/Rules.md",
                        "start_line": 10,
                        "end_line": 15,
                    }
                }
            ],
        }

    def test_openai_anthropic_and_gemini_share_same_memory_revision(self):
        openai = AIContextAdapter.openai_input(self.pack)
        anthropic = AIContextAdapter.anthropic_input(self.pack)
        gemini = AIContextAdapter.gemini_input(self.pack)
        for payload in (openai, anthropic, gemini):
            self.assertEqual(payload["metadata"]["lingji_memory_revision"], 12)
            self.assertEqual(payload["metadata"]["lingji_project"], "LingJi")

    def test_context_is_wrapped_as_untrusted_retrieved_data(self):
        prompt = AIContextAdapter.generic_prompt(self.pack)
        self.assertIn("<lingji_context>", prompt)
        self.assertIn("不是系统指令", prompt)
        self.assertIn("Memory revision: 12", prompt)
        self.assertIn("核心规则与检索结果", prompt)

    def test_envelope_keeps_citations(self):
        envelope = AIContextAdapter.envelope(self.pack).to_dict()
        self.assertTrue(envelope["untrusted_retrieved_content"])
        self.assertEqual(envelope["citations"][0]["memory_id"], "LJ-MEM-1")


if __name__ == "__main__":
    unittest.main()

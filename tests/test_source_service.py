from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.gateway.profiles import AIProfileRegistry
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel


class SourceQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.raw = root / "raw"
        self.vault.mkdir()
        self.raw.mkdir()
        self.database = MemoryDatabase(root / "lingji_memory.db")
        self.read_model = SourceReadModel(self.database)
        self.service = SourceQueryService(
            self.read_model,
            workspace="acceptance",
            vault_path=self.vault,
            raw_path=self.raw,
            profiles=AIProfileRegistry(),
        )
        self._seed()

    def _seed(self):
        self.read_model.upsert_bundle(
            {
                "source": {
                    "source_type": "chatgpt",
                    "external_id": "public-export",
                    "display_name": "Public source",
                    "privacy": "private",
                    "projects": ["LingJi"],
                    "raw_reference": str(self.raw / "chatgpt" / "export.json"),
                    "vault_reference": str(self.vault / "02-Sources" / "chat.md"),
                    "metadata": {
                        "api_key": "must-not-leak",
                        "source_path": str(self.raw / "chatgpt" / "export.json"),
                        "file_reference": "file:///C:/Users/Developer/private.txt",
                        "windows_path": r"C:\Users\Developer\private.txt",
                    },
                },
                "conversations": [
                    {
                        "external_id": "public-conversation",
                        "title": "Visible conversation",
                        "messages": [
                            {
                                "external_id": "public-message",
                                "role": "user",
                                "sequence": 1,
                                "content": "visible message body",
                            }
                        ],
                    }
                ],
            }
        )
        self.read_model.upsert_bundle(
            {
                "source": {
                    "source_type": "chatgpt",
                    "external_id": "restricted-export",
                    "display_name": "Restricted source",
                    "privacy": "restricted",
                    "agent_scope": ["ollama"],
                },
                "conversations": [
                    {
                        "external_id": "restricted-conversation",
                        "title": "Restricted conversation",
                        "messages": [
                            {
                                "external_id": "restricted-message",
                                "role": "assistant",
                                "sequence": 1,
                                "content": "restricted message body",
                            }
                        ],
                    }
                ],
            }
        )

    def test_owner_list_uses_workspace_and_does_not_return_message_body(self):
        response = self.service.list_messages()
        self.assertEqual(response["workspace"], "acceptance")
        self.assertEqual(response["viewer_scope"], "owner")
        self.assertEqual(response["pagination"]["total"], 2)
        self.assertNotIn("content", response["items"][0])

    def test_detail_returns_content_only_after_explicit_request(self):
        message_id = self.service.list_messages(q="visible")["items"][0]["message_id"]
        detail = self.service.get_message(message_id)
        self.assertEqual(detail["item"]["content"], "visible message body")

    def test_remote_profile_cannot_read_restricted_source(self):
        chatgpt = self.service.agent_viewer("chatgpt")
        ollama = self.service.agent_viewer("ollama")
        self.assertEqual(self.service.list_sources(viewer=chatgpt)["pagination"]["total"], 1)
        restricted = self.service.list_sources(viewer=ollama, privacy="restricted")
        self.assertEqual(restricted["pagination"]["total"], 1)
        source_id = restricted["items"][0]["source_id"]
        with self.assertRaises(PermissionError):
            self.service.get_source(source_id, viewer=chatgpt)

    def test_source_permission_tightening_updates_inherited_children(self):
        chatgpt = self.service.agent_viewer("chatgpt")
        ollama = self.service.agent_viewer("ollama")
        conversation_id = self.service.list_conversations(
            viewer=chatgpt, q="Visible conversation"
        )["items"][0]["conversation_id"]
        message_id = self.service.list_messages(viewer=chatgpt, q="visible message")["items"][0][
            "message_id"
        ]

        self.read_model.upsert_source(
            {
                "source_type": "chatgpt",
                "external_id": "public-export",
                "display_name": "Public source",
                "privacy": "restricted",
                "agent_scope": ["ollama"],
            }
        )

        self.assertEqual(
            self.service.list_conversations(viewer=chatgpt, q="Visible conversation")[
                "pagination"
            ]["total"],
            0,
        )
        self.assertEqual(
            self.service.list_messages(viewer=chatgpt, q="visible message")["pagination"][
                "total"
            ],
            0,
        )
        with self.assertRaises(PermissionError):
            self.service.get_conversation(conversation_id, viewer=chatgpt)
        with self.assertRaises(PermissionError):
            self.service.get_message(message_id, viewer=chatgpt)
        self.assertEqual(
            self.service.list_messages(viewer=ollama, q="visible message")["pagination"][
                "total"
            ],
            1,
        )

    def test_explicit_child_permissions_are_not_overwritten(self):
        result = self.read_model.upsert_bundle(
            {
                "source": {
                    "source_type": "chatgpt",
                    "external_id": "explicit-export",
                    "display_name": "Explicit source",
                    "privacy": "private",
                    "agent_scope": ["chatgpt"],
                },
                "conversations": [
                    {
                        "external_id": "explicit-conversation",
                        "title": "Explicit conversation",
                        "privacy": "private",
                        "agent_scope": ["chatgpt"],
                        "messages": [
                            {
                                "external_id": "explicit-message",
                                "role": "user",
                                "sequence": 1,
                                "content": "explicit child body",
                                "privacy": "private",
                                "agent_scope": ["chatgpt"],
                            }
                        ],
                    }
                ],
            }
        )
        self.read_model.upsert_source(
            {
                "source_type": "chatgpt",
                "external_id": "explicit-export",
                "display_name": "Explicit source",
                "privacy": "restricted",
                "agent_scope": ["ollama"],
            }
        )

        chatgpt = self.service.agent_viewer("chatgpt")
        conversation = self.service.list_conversations(
            viewer=chatgpt, q="Explicit conversation"
        )
        message = self.service.list_messages(viewer=chatgpt, q="explicit child")
        self.assertEqual(conversation["pagination"]["total"], 1)
        self.assertEqual(message["pagination"]["total"], 1)
        self.assertEqual(conversation["items"][0]["privacy"], "private")
        self.assertEqual(message["items"][0]["privacy"], "private")
        self.assertEqual(result["sources"], 1)

    def test_agent_scope_update_is_immediate_for_inherited_children(self):
        self.read_model.upsert_bundle(
            {
                "source": {
                    "source_type": "chatgpt",
                    "external_id": "scope-export",
                    "display_name": "Scope source",
                    "privacy": "private",
                    "agent_scope": ["chatgpt"],
                },
                "conversations": [
                    {
                        "external_id": "scope-conversation",
                        "title": "Scope conversation",
                        "messages": [
                            {
                                "external_id": "scope-message",
                                "role": "user",
                                "sequence": 1,
                                "content": "scope body",
                            }
                        ],
                    }
                ],
            }
        )
        chatgpt = self.service.agent_viewer("chatgpt")
        ollama = self.service.agent_viewer("ollama")
        self.assertEqual(
            self.service.list_messages(viewer=chatgpt, q="scope body")["pagination"]["total"],
            1,
        )

        self.read_model.upsert_source(
            {
                "source_type": "chatgpt",
                "external_id": "scope-export",
                "display_name": "Scope source",
                "privacy": "private",
                "agent_scope": ["ollama"],
            }
        )

        self.assertEqual(
            self.service.list_messages(viewer=chatgpt, q="scope body")["pagination"]["total"],
            0,
        )
        self.assertEqual(
            self.service.list_messages(viewer=ollama, q="scope body")["pagination"]["total"],
            1,
        )

    def test_filters_and_safe_references(self):
        result = self.service.list_sources(
            source_type="chatgpt", project="LingJi", q="Public"
        )
        self.assertEqual(result["pagination"]["total"], 1)
        item = result["items"][0]
        self.assertTrue(item["raw_reference"].startswith("raw:"))
        self.assertTrue(item["vault_reference"].startswith("vault:"))
        self.assertNotIn("api_key", item["metadata"])
        self.assertTrue(item["metadata"]["source_path"].startswith("raw:"))
        self.assertIsNone(item["metadata"]["file_reference"])
        self.assertIsNone(item["metadata"]["windows_path"])

    def test_disallowed_requested_privacy_returns_empty_page(self):
        chatgpt = self.service.agent_viewer("chatgpt")
        response = self.service.list_sources(viewer=chatgpt, privacy="restricted")
        self.assertEqual(response["pagination"]["total"], 0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sqlite3
import unittest

from fastapi.testclient import TestClient

from src.control.api import create_control_app
from src.gateway.memory_inspector import ReadModelUnavailableError


class FakeInspector:
    def status(self):
        return {"workspace": "acceptance", "viewer_scope": "owner", "state": "healthy"}

    def list_sources(self, **kwargs):
        return {
            "workspace": "acceptance",
            "viewer_scope": "owner",
            "items": [],
            "pagination": {
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
                "total": 0,
                "has_more": False,
            },
        }

    def get_source(self, source_id):
        if source_id == "missing":
            raise LookupError("source not found")
        return {"workspace": "acceptance", "item": {"source_id": source_id}}

    def list_conversations(self, **kwargs):
        return {
            "workspace": "acceptance",
            "items": [],
            "pagination": {
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
                "total": 0,
                "has_more": False,
            },
        }

    def get_conversation(self, conversation_id):
        return {"workspace": "acceptance", "item": {"conversation_id": conversation_id}}

    def list_messages(self, **kwargs):
        return {
            "workspace": "acceptance",
            "items": [],
            "pagination": {
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
                "total": 0,
                "has_more": False,
            },
        }

    def get_message(self, message_id):
        return {
            "workspace": "acceptance",
            "item": {"message_id": message_id, "content": "detail"},
        }

    def list_memories(self, **kwargs):
        return {
            "workspace": "acceptance",
            "items": [],
            "pagination": {
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
                "total": 0,
                "has_more": False,
            },
        }

    def get_memory(self, memory_id):
        if memory_id == "missing":
            raise LookupError("memory not found")
        return {"workspace": "acceptance", "item": {"memory_id": memory_id}}

    def memory_source(self, memory_id):
        return {"workspace": "acceptance", "memory_id": memory_id, "links": []}

    def memory_vector(self, memory_id):
        return {
            "workspace": "acceptance",
            "memory_id": memory_id,
            "vector": {
                "chunks": [
                    {
                        "chunk_id": "CHUNK-1",
                        "exists": None,
                        "source": "unavailable",
                    }
                ]
            },
        }


class UnavailableInspector(FakeInspector):
    def status(self):
        raise ReadModelUnavailableError("internal read model failure")


class SqliteUnavailableInspector(FakeInspector):
    def status(self):
        raise sqlite3.OperationalError(
            r"unable to open D:\Users\Secret\lingji_memory.db; fallback C:\Users\Owner\memory.db"
        )


class FakeControl:
    def __init__(self, inspector):
        self.memory_inspector = inspector


class MemoryInspectorApiTests(unittest.TestCase):
    def client(self, inspector=None):
        context = TestClient(
            create_control_app(
                object(),
                service=FakeControl(inspector or FakeInspector()),
                token="secret",
            )
        )
        client = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        return client

    def test_factory_is_direct_api_implementation_without_monkey_patch_marker(self):
        self.assertEqual(create_control_app.__module__, "src.control.api")
        self.assertFalse(hasattr(create_control_app, "_lingji_read_model_contract"))

    def test_token_is_required(self):
        client = self.client()
        self.assertEqual(client.get("/api/memory/inspector/status").status_code, 401)
        self.assertEqual(
            client.get(
                "/api/memory/inspector/status",
                headers={"X-LingJi-Token": "wrong"},
            ).status_code,
            401,
        )

    def test_authenticated_read_routes_and_pagination(self):
        client = self.client()
        headers = {"X-LingJi-Token": "secret"}
        status = client.get("/api/memory/inspector/status", headers=headers)
        sources = client.get(
            "/api/memory/inspector/sources?limit=20&offset=0", headers=headers
        )
        vector = client.get(
            "/api/memory/inspector/memories/MEM-1/vector", headers=headers
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(sources.status_code, 200)
        self.assertEqual(sources.json()["pagination"]["limit"], 20)
        self.assertIsNone(vector.json()["vector"]["chunks"][0]["exists"])
        self.assertNotIn("raw_vector", vector.text)

    def test_missing_entity_returns_404_and_bad_pagination_returns_422(self):
        client = self.client()
        headers = {"X-LingJi-Token": "secret"}
        self.assertEqual(
            client.get(
                "/api/memory/inspector/sources/missing", headers=headers
            ).status_code,
            404,
        )
        self.assertEqual(
            client.get(
                "/api/memory/inspector/sources?offset=-1", headers=headers
            ).status_code,
            422,
        )
        self.assertEqual(
            client.get(
                "/api/memory/inspector/sources?limit=201", headers=headers
            ).status_code,
            422,
        )

    def test_read_model_unavailable_returns_stable_503(self):
        client = self.client(UnavailableInspector())
        response = client.get(
            "/api/memory/inspector/status",
            headers={"X-LingJi-Token": "secret"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "READ_MODEL_UNAVAILABLE")
        self.assertEqual(
            response.json()["detail"]["message"],
            "Structured read model is unavailable",
        )

    def test_sqlite_read_failure_does_not_leak_local_paths(self):
        client = self.client(SqliteUnavailableInspector())
        response = client.get(
            "/api/memory/inspector/status",
            headers={"X-LingJi-Token": "secret"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "READ_MODEL_UNAVAILABLE")
        self.assertEqual(
            response.json()["detail"]["message"],
            "Structured read model is unavailable",
        )
        for forbidden in ("C:\\", "D:\\", "Users", "lingji_memory.db", "memory.db"):
            self.assertNotIn(forbidden, response.text)

    def test_all_inspector_routes_are_read_only(self):
        app = create_control_app(
            object(),
            service=FakeControl(FakeInspector()),
            token="secret",
        )
        routes = [
            route
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/memory/inspector")
        ]
        self.assertTrue(routes)
        self.assertTrue(all(set(route.methods or ()) <= {"GET", "HEAD"} for route in routes))


if __name__ == "__main__":
    unittest.main()

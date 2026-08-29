from __future__ import annotations

from fastapi.testclient import TestClient

from src.control.api import create_control_app


class CardInspector:
    def list_cards(self, **kwargs):
        assert kwargs["limit"] <= 50
        assert kwargs["offset"] >= 0
        return {
            "workspace": "acceptance",
            "viewer_scope": "owner",
            "items": [{"memory_id": "mem-1", "topic": "Safe topic", "action": {"type": "review"}}],
            "pagination": {"limit": kwargs["limit"], "offset": kwargs["offset"], "total": 7, "has_more": True},
        }

    def get_card(self, memory_id, **kwargs):
        return {
            "workspace": "acceptance",
            "item": {
                "memory_id": memory_id,
                "topic": "Safe topic",
                "evidence": [{"message_id": "msg-1", "preview": "bounded"}],
            },
        }


class Control:
    def __init__(self):
        self.memory_inspector = CardInspector()


def client():
    context = TestClient(create_control_app(object(), service=Control(), token="secret"))
    return context


def test_cards_are_authenticated_filtered_and_stably_paginated():
    with client() as app:
        response = app.get(
            "/api/memory/inspector/cards?state=current&action=review&source=src-1&limit=2&offset=4",
            headers={"X-LingJi-Token": "secret"},
        )
        assert response.status_code == 200
        assert response.json()["pagination"] == {"limit": 2, "offset": 4, "total": 7, "has_more": True}
        assert "full body" not in response.text


def test_card_detail_expands_bounded_evidence_and_auth_is_required():
    with client() as app:
        assert app.get("/api/memory/inspector/cards").status_code == 401
        response = app.get(
            "/api/memory/inspector/cards/mem-1?expand=true",
            headers={"X-LingJi-Token": "secret"},
        )
        assert response.status_code == 200
        assert response.json()["item"]["evidence"][0]["preview"] == "bounded"


def test_cards_limit_is_restricted_to_one_through_fifty():
    with client() as app:
        response = app.get(
            "/api/memory/inspector/cards?limit=51",
            headers={"X-LingJi-Token": "secret"},
        )
        assert response.status_code == 422

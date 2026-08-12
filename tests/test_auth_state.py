from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.auth_state import AuthState, AuthStatusService, InMemoryCredentialStore, export_auth_snapshot
from src.storage.state_db import StateDatabase


class AuthStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = StateDatabase(self.root / "lingji_state.db")
        self.credentials = InMemoryCredentialStore()
        self.service = AuthStatusService(self.database, self.credentials)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_credential_presence_persists_only_non_secret_status(self) -> None:
        self.credentials.set("github", "fake-token-must-not-persist")

        status = self.service.refresh_presence("github", auth_method="token")

        self.assertEqual(status["state"], AuthState.CREDENTIAL_PRESENT.value)
        self.assertTrue(status["credential_present"])
        persisted = self.database.get_auth_status("github")
        self.assertEqual(persisted["state"], AuthState.CREDENTIAL_PRESENT.value)
        self.assertNotIn("fake-token-must-not-persist", self.database.path.read_text(errors="ignore"))

    def test_fake_store_supports_credential_lifecycle(self) -> None:
        self.assertFalse(self.credentials.exists("codex"))
        self.credentials.set("codex", "fake-secret")
        self.assertEqual(self.credentials.get("codex"), "fake-secret")
        self.assertTrue(self.credentials.exists("codex"))
        self.credentials.delete("codex")
        self.assertIsNone(self.credentials.get("codex"))
        with self.assertRaises(Exception):
            self.credentials.set("codex", "")

    def test_verified_status_survives_service_restart(self) -> None:
        self.service.record(
            "github",
            auth_method="token",
            state=AuthState.VERIFIED,
            credential_present=True,
            credential_valid=True,
            permissions_ok=True,
            account_bound=True,
        )

        restored = AuthStatusService(self.database, self.credentials).status("github")

        self.assertEqual(restored["state"], AuthState.VERIFIED.value)
        self.assertTrue(restored["permissions_ok"])

    def test_state_machine_keeps_non_secret_outcomes(self) -> None:
        for state in (AuthState.VERIFYING, AuthState.EXPIRED, AuthState.INVALID, AuthState.PERMISSION_INSUFFICIENT):
            recorded = self.service.record(
                "github", auth_method="token", state=state, credential_present=True,
                credential_valid=state == AuthState.VERIFYING,
            )
            self.assertEqual(recorded["state"], state.value)

    def test_allowlist_snapshot_omits_fake_token_cookie_and_authorization(self) -> None:
        self.service.record(
            "github",
            auth_method="token",
            state=AuthState.VERIFIED,
            credential_present=True,
            credential_valid=True,
            permissions_ok=True,
            account_bound=True,
        )
        destination = self.root / "LOCAL_AUTH_STATUS_PR88.json"

        snapshot = export_auth_snapshot(
            self.database,
            destination,
            task_id="PR88-M5-PHASE4-FAILURE-REPAIR-171091FE",
            platform="test",
            untrusted={
                "token": "fake-token-must-not-export",
                "cookie": "fake-cookie-must-not-export",
                "Authorization": "Bearer fake-token-must-not-export",
            },
        )

        raw = destination.read_text(encoding="utf-8")
        self.assertEqual(snapshot["secret_export_count"], 0)
        self.assertNotIn("fake-token-must-not-export", raw)
        self.assertNotIn("fake-cookie-must-not-export", raw)
        for forbidden in ("Authorization:", "Bearer ", "sk-", "ghp_", "access_token", "refresh_token", "api_key", "cookie", "session"):
            self.assertNotIn(forbidden.lower(), raw.lower())
        self.assertEqual(set(json.loads(raw)["providers"]["github"]), {
            "credential_present",
            "state",
            "permissions_ok",
        })


if __name__ == "__main__":
    unittest.main()

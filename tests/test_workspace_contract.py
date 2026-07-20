import json
import tempfile
import unittest
from pathlib import Path

from src.config import Settings
from src.runtime.workspace import (
    WorkspaceName,
    WorkspaceResolver,
    WorkspaceValidationError,
)


class WorkspaceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            workspace_name="production",
            workspace_root=str(self.root / "workspace-root"),
            production_qdrant_collection="lingji_memory_production",
            acceptance_qdrant_collection="lingji_memory_acceptance",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_workspaces_are_physically_isolated_and_serializable(self):
        contexts = WorkspaceResolver.resolve_all(
            self.settings,
            environ={},
            project_root=self.root,
        )
        production = contexts[WorkspaceName.PRODUCTION]
        acceptance = contexts[WorkspaceName.ACCEPTANCE]
        self.assertNotEqual(production.qdrant_collection, acceptance.qdrant_collection)
        self.assertNotEqual(production.vault_path, acceptance.vault_path)
        self.assertNotEqual(production.raw_path, acceptance.raw_path)
        self.assertNotEqual(production.state_db_path, acceptance.state_db_path)
        self.assertNotEqual(production.memory_db_path, acceptance.memory_db_path)
        self.assertNotEqual(production.queue_db_path, acceptance.queue_db_path)
        self.assertNotEqual(production.reports_path, acceptance.reports_path)
        self.assertNotEqual(production.temp_path, acceptance.temp_path)
        for left in production.mutable_paths().values():
            for right in acceptance.mutable_paths().values():
                self.assertFalse(str(left).casefold() == str(right).casefold())
        json.dumps(production.to_dict())
        self.assertFalse(production.storage_path.exists())
        self.assertFalse(acceptance.storage_path.exists())

    def test_resolution_precedence_is_override_then_environment_then_settings(self):
        self.settings.production_vault_dir = "settings-vault"
        environment = {"LINGJI_PRODUCTION_VAULT": "environment-vault"}
        context = WorkspaceResolver.resolve(
            self.settings,
            "production",
            {"vault_path": "override-vault"},
            environ=environment,
            project_root=self.root,
        )
        self.assertEqual(context.vault_path, (self.root / "override-vault").resolve())

        environment_context = WorkspaceResolver.resolve(
            self.settings,
            "production",
            environ=environment,
            project_root=self.root,
        )
        self.assertEqual(
            environment_context.vault_path,
            (self.root / "environment-vault").resolve(),
        )

        settings_context = WorkspaceResolver.resolve(
            self.settings,
            "production",
            environ={},
            project_root=self.root,
        )
        self.assertEqual(settings_context.vault_path, (self.root / "settings-vault").resolve())

    def test_unknown_workspace_fails_instead_of_falling_back(self):
        with self.assertRaisesRegex(WorkspaceValidationError, "Unknown workspace"):
            WorkspaceResolver.resolve(
                self.settings,
                "preview",
                environ={},
                project_root=self.root,
            )

    def test_equal_or_nested_paths_fail_isolation(self):
        shared = self.root / "shared"
        production = WorkspaceResolver.resolve(
            self.settings,
            "production",
            {"storage_path": shared},
            environ={},
            project_root=self.root,
        )
        acceptance = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            {"storage_path": shared / "acceptance"},
            environ={},
            project_root=self.root,
        )
        with self.assertRaisesRegex(WorkspaceValidationError, "Workspace isolation failed"):
            WorkspaceResolver.validate_isolation(production, acceptance)

    def test_remote_qdrant_url_may_be_shared_but_collection_must_differ(self):
        production = WorkspaceResolver.resolve(
            self.settings,
            "production",
            {
                "qdrant_mode": "remote",
                "qdrant_url": "http://127.0.0.1:6333",
                "qdrant_collection": "prod",
            },
            environ={},
            project_root=self.root,
        )
        acceptance = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            {
                "qdrant_mode": "remote",
                "qdrant_url": "http://127.0.0.1:6333",
                "qdrant_collection": "acceptance",
            },
            environ={},
            project_root=self.root,
        )
        WorkspaceResolver.validate_isolation(production, acceptance)
        duplicate_collection = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            {
                "qdrant_mode": "remote",
                "qdrant_url": "http://127.0.0.1:6333",
                "qdrant_collection": "PROD",
            },
            environ={},
            project_root=self.root,
        )
        with self.assertRaisesRegex(WorkspaceValidationError, "Qdrant collection"):
            WorkspaceResolver.validate_isolation(production, duplicate_collection)

    def test_acceptance_cannot_reuse_production_vault(self):
        production = WorkspaceResolver.resolve(
            self.settings,
            "production",
            environ={},
            project_root=self.root,
        )
        acceptance = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            {"vault_path": production.vault_path},
            environ={},
            project_root=self.root,
        )
        with self.assertRaisesRegex(WorkspaceValidationError, "vault_path"):
            WorkspaceResolver.validate_isolation(production, acceptance)

    def test_case_and_dotdot_aliases_are_rejected(self):
        production = WorkspaceResolver.resolve(
            self.settings,
            "production",
            {"storage_path": self.root / "AliasRoot"},
            environ={},
            project_root=self.root,
        )
        acceptance = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            {"storage_path": self.root / "aliasroot" / "child" / ".."},
            environ={},
            project_root=self.root,
        )
        with self.assertRaisesRegex(WorkspaceValidationError, "Workspace isolation failed"):
            WorkspaceResolver.validate_isolation(production, acceptance)

    def test_windows_system_drive_is_rejected_before_any_write(self):
        with self.assertRaisesRegex(WorkspaceValidationError, "system drive"):
            WorkspaceResolver.resolve(
                self.settings,
                "production",
                {"storage_path": r"C:\\LingJi\\production"},
                environ={},
                project_root=self.root,
            )


if __name__ == "__main__":
    unittest.main()

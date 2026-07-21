import json
import os
import string
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Settings
from src.runtime.workspace import (
    WorkspaceName,
    WorkspaceResolver,
    WorkspaceValidationError,
)


def _synthetic_non_system_windows_root() -> Path:
    system_drive = str(os.environ.get("SystemDrive", "C:")).rstrip("\\/").casefold()
    drive = next(
        f"{letter}:"
        for letter in string.ascii_uppercase
        if f"{letter}:".casefold() != system_drive
    )
    return Path(drive + "\\LingJiSyntheticTest")


class WorkspaceContractTests(unittest.TestCase):
    def setUp(self):
        import platform
        import uuid

        if platform.system() == "Windows":
            self._managed = None
            self.root = _synthetic_non_system_windows_root() / uuid.uuid4().hex
        else:
            self._managed = tempfile.TemporaryDirectory()
            self.root = Path(self._managed.name)
        self.settings = Settings(
            _env_file=None,
            workspace_name="production",
            workspace_root=str(self.root / "workspace-root"),
            production_qdrant_collection="lingji_memory_production",
            acceptance_qdrant_collection="lingji_memory_acceptance",
        )

    def tearDown(self):
        if self._managed is not None:
            self._managed.cleanup()

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
        self.assertNotEqual(production.backup_path, acceptance.backup_path)
        self.assertNotEqual(production.reports_path, acceptance.reports_path)
        self.assertNotEqual(production.temp_path, acceptance.temp_path)
        for left in production.mutable_paths().values():
            for right in acceptance.mutable_paths().values():
                self.assertFalse(str(left).casefold() == str(right).casefold())
        json.dumps(production.to_dict())
        self.assertFalse(production.storage_path.exists())
        self.assertFalse(acceptance.storage_path.exists())

    def test_default_backup_path_is_storage_backups(self):
        context = WorkspaceResolver.resolve(
            self.settings,
            "production",
            environ={},
            project_root=self.root,
        )
        self.assertEqual(context.backup_path, context.storage_path / "backups")

    def test_workspace_backup_environment_override(self):
        target = self.root / "external-backup"
        context = WorkspaceResolver.resolve(
            self.settings,
            "production",
            environ={"LINGJI_PRODUCTION_BACKUP": str(target)},
            project_root=self.root,
        )
        self.assertEqual(context.backup_path, target.resolve())

    def test_settings_backup_path_defaults_to_legacy_storage_backups(self):
        settings = Settings(_env_file=None, storage_dir="storage", backup_dir="")
        self.assertEqual(settings.backup_path, Path("storage/backups").resolve())

    def test_settings_backup_path_preserves_explicit_relative_and_absolute_values(self):
        relative = Settings(_env_file=None, backup_dir="owner/backups")
        self.assertEqual(relative.backup_path, Path("owner/backups").resolve())
        absolute_target = (self.root / "absolute-backup").resolve()
        absolute = Settings(_env_file=None, backup_dir=str(absolute_target))
        self.assertEqual(absolute.backup_path, absolute_target)

    def test_settings_backup_environment_override_remains_compatible(self):
        target = (self.root / "environment-backup").resolve()
        with patch.dict(os.environ, {"BACKUP_DIR": str(target)}, clear=False):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.backup_path, target)

    def test_settings_default_contains_no_machine_specific_backup_path(self):
        settings = Settings(_env_file=None)
        normalized = str(settings.backup_dir).replace("\\", "/").casefold()
        self.assertNotIn("d:/codex", normalized)
        self.assertNotIn("/users/", normalized)

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

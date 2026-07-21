"""Obsidian CLI compatibility and portable-discovery tests."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from second_brain.obsidian_cli import (
    DEFAULT_CLI_PATHS,
    DISCOVERY_ENVIRONMENT,
    DISCOVERY_NOT_FOUND,
    DISCOVERY_PATH,
    DISCOVERY_PLATFORM_LOCATION,
    ObsidianCli,
    ObsidianCliConfig,
    ObsidianCliError,
    ObsidianCliErrorResult,
    ObsidianCliNotFound,
    ObsidianCliTimeout,
    ObsidianNote,
    ObsidianVaultInfo,
)


def _touch_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stub", encoding="utf-8")
    return path


@pytest.fixture
def mock_cli_config(tmp_path):
    cli_path = _touch_file(tmp_path / "Obsidian" / "Obsidian.com")
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    return ObsidianCliConfig(
        cli_path=str(cli_path),
        vault_path=str(vault_path),
        vault_name="本地知识库",
        timeout=15,
        dry_run=False,
    )


@pytest.fixture
def mock_dry_run_config(mock_cli_config):
    mock_cli_config.dry_run = True
    return mock_cli_config


def test_environment_cli_has_highest_priority(tmp_path, monkeypatch):
    explicit = _touch_file(tmp_path / "custom" / "Obsidian.com")
    path_cli = _touch_file(tmp_path / "bin" / "Obsidian.com")
    monkeypatch.setattr(
        "second_brain.obsidian_cli.shutil.which",
        lambda *args, **kwargs: str(path_cli),
    )
    result = ObsidianCliConfig.discover(
        environ={"OBSIDIAN_CLI_PATH": str(explicit), "PATH": str(path_cli.parent)}
    )
    assert result.path == str(explicit)
    assert result.source == DISCOVERY_ENVIRONMENT


def test_path_discovery_checks_both_supported_names(tmp_path, monkeypatch):
    cli_path = _touch_file(tmp_path / "bin" / "obsidian")
    calls: list[str] = []

    def fake_which(name, path=None):
        calls.append(name)
        return str(cli_path) if name == "obsidian" else None

    monkeypatch.setattr("second_brain.obsidian_cli.shutil.which", fake_which)
    result = ObsidianCliConfig.discover(
        environ={"PATH": str(cli_path.parent)}, platform="linux"
    )
    assert result.path == str(cli_path)
    assert result.source == DISCOVERY_PATH
    assert calls == ["Obsidian.com", "obsidian"]


@pytest.mark.parametrize("variable", ["LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"])
def test_windows_standard_locations_are_derived_from_environment(
    variable, tmp_path, monkeypatch
):
    root = tmp_path / variable.replace("(", "_").replace(")", "")
    expected = _touch_file(root / "Obsidian" / "Obsidian.com")
    monkeypatch.setattr(
        "second_brain.obsidian_cli.shutil.which", lambda *args, **kwargs: None
    )
    result = ObsidianCliConfig.discover(
        environ={variable: str(root), "PATH": ""}, platform="win32"
    )
    assert result.path == str(expected)
    assert result.source == DISCOVERY_PLATFORM_LOCATION


def test_discovery_not_found_is_stable(monkeypatch):
    monkeypatch.setattr(
        "second_brain.obsidian_cli.shutil.which", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    result = ObsidianCliConfig.discover(environ={"PATH": ""}, platform="linux")
    assert result.path == ""
    assert result.source == DISCOVERY_NOT_FOUND


def test_vault_priority_workspace_runtime_then_environment(tmp_path):
    config = ObsidianCliConfig.from_env(
        workspace_vault_path=tmp_path / "workspace",
        runtime_vault_path=tmp_path / "runtime",
        environ={"OBSIDIAN_VAULT_PATH": str(tmp_path / "environment")},
    )
    assert config.vault_path == str(tmp_path / "workspace")
    assert config.vault_discovery_source == "workspace"

    runtime_config = ObsidianCliConfig.from_env(
        runtime_vault_path=tmp_path / "runtime",
        environ={"OBSIDIAN_VAULT_PATH": str(tmp_path / "environment")},
    )
    assert runtime_config.vault_path == str(tmp_path / "runtime")
    assert runtime_config.vault_discovery_source == "runtime_settings"

    environment_config = ObsidianCliConfig.from_env(
        environ={"OBSIDIAN_VAULT_PATH": str(tmp_path / "environment")}
    )
    assert environment_config.vault_path == str(tmp_path / "environment")
    assert environment_config.vault_discovery_source == DISCOVERY_ENVIRONMENT


def test_legacy_vault_environment_remains_supported(tmp_path):
    config = ObsidianCliConfig.from_env(
        environ={"SECOND_BRAIN_OBSIDIAN_DIR": str(tmp_path)}
    )
    assert config.vault_path == str(tmp_path)
    assert config.vault_discovery_source == DISCOVERY_ENVIRONMENT


    config = ObsidianCliConfig.from_env(environ={"PATH": ""})
    assert isinstance(config, ObsidianCliConfig)
    assert config.timeout > 0
    assert config.vault_name == "本地知识库"


def test_config_from_env_defaults():
    config = ObsidianCliConfig.from_env(environ={"PATH": ""})
    assert isinstance(config, ObsidianCliConfig)
    assert config.timeout > 0
    assert config.vault_name == "本地知识库"


def test_source_code_does_not_contain_developer_specific_paths():
    import inspect
    from second_brain import obsidian_cli as oc
    src = inspect.getsource(oc)
    assert "D:\\codex" not in src
    assert "C:\\Users" not in src


def test_synthetic_localappdata_generates_programs_and_direct_path():
    from second_brain.obsidian_cli import _platform_cli_candidates
    env = {"LOCALAPPDATA": "D:\\Test\\AppData", "ProgramFiles": "D:\\Test\\Program Files", "ProgramFiles(x86)": "D:\\Test\\Program Files (x86)", "PATH": ""}
    paths = _platform_cli_candidates(platform="win32", environ=env)
    assert any("Programs" in str(p) for p in paths)
    assert any(str(p).endswith("Obsidian.com") for p in paths)
    assert len(paths) >= 2


def test_candidate_paths_change_when_environment_changes():
    from second_brain.obsidian_cli import _platform_cli_candidates
    env_a = {"LOCALAPPDATA": "D:\\A", "ProgramFiles": "D:\\B", "ProgramFiles(x86)": "D:\\C", "PATH": ""}
    env_b = {"LOCALAPPDATA": "D:\\X", "ProgramFiles": "D:\\Y", "ProgramFiles(x86)": "D:\\Z", "PATH": ""}
    paths_a = _platform_cli_candidates(platform="win32", environ=env_a)
    paths_b = _platform_cli_candidates(platform="win32", environ=env_b)
    assert paths_a != paths_b
    assert any("D:\\A" in str(p) for p in paths_a)
    assert any("D:\\X" in str(p) for p in paths_b)



def test_vault_name_from_environment_variable():
    config = ObsidianCliConfig.from_env(
        environ={"PATH": "", "OBSIDIAN_VAULT_NAME": "工作知识库"}
    )
    assert config.vault_name == "工作知识库"


def test_vault_name_from_vault_path_when_env_not_set():
    config = ObsidianCliConfig.from_env(
        workspace_vault_path="D:\\test\\main-vault",
        environ={"PATH": ""},
    )
    assert config.vault_name == "main-vault"


def test_vault_name_defaults_when_neither_path_nor_env():
    config = ObsidianCliConfig.from_env(environ={"PATH": ""})
    assert config.vault_name == "本地知识库"


def test_resolve_vault_name_env_has_highest_priority():
    from second_brain.obsidian_cli import ObsidianCliConfig
    result = ObsidianCliConfig._resolve_vault_name(
        vault_path="D:\\other\\vault",
        environ={"OBSIDIAN_VAULT_NAME": "环境优先"},
    )
    assert result == "环境优先"


def test_resolve_vault_name_falls_back_to_path_name():
    from second_brain.obsidian_cli import ObsidianCliConfig
    result = ObsidianCliConfig._resolve_vault_name(
        vault_path="D:\\my-vault",
        environ={},
    )
    assert result == "my-vault"


def test_invalid_timeout_falls_back_to_default():
    config = ObsidianCliConfig.from_env(
        environ={"PATH": "", "OBSIDIAN_CLI_TIMEOUT": "invalid"}
    )
    assert config.timeout == 15


def test_config_validation_no_cli(tmp_path):
    config = ObsidianCliConfig(
        cli_path="", vault_path=str(tmp_path), vault_name="test"
    )
    issues = config.validate()
    assert any("CLI" in issue for issue in issues)


def test_config_validation_ok(mock_cli_config):
    assert mock_cli_config.validate() == []


def test_error_hierarchy():
    assert issubclass(ObsidianCliNotFound, ObsidianCliError)
    assert issubclass(ObsidianCliTimeout, ObsidianCliError)
    assert issubclass(ObsidianCliErrorResult, ObsidianCliError)


def test_error_message():
    error = ObsidianCliError("测试错误", command="test", rc=1, err="stderr")
    assert str(error) == "测试错误"
    assert error.command == "test"
    assert error.returncode == 1
    assert error.stderr == "stderr"


def test_sanitize_filename():
    assert ObsidianCli.sanitize_filename("normal_file.md") == "normal_file.md"
    assert "/" not in ObsidianCli.sanitize_filename("a/b:c*d?e")
    assert "\\" not in ObsidianCli.sanitize_filename("a\\b")
    assert ObsidianCli.sanitize_filename("") == ""


def test_validate_path():
    assert ObsidianCli.validate_path("notes/test.md")
    assert ObsidianCli.validate_path("PEMIS/dashboard/Control Center.md")
    assert not ObsidianCli.validate_path("../outside.md")
    assert not ObsidianCli.validate_path("notes/../../../etc/passwd")


def test_dry_run_no_writes(mock_dry_run_config, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("dry-run must not call subprocess"),
    )
    cli = ObsidianCli(config=mock_dry_run_config)
    result = cli.create("test/dry-run-test.md", "测试内容", overwrite=False)
    assert result == ""
    assert cli.operation_log[-1]["dry_run"] is True


def test_timeout_is_translated(mock_cli_config, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 1))

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ObsidianCliTimeout):
        ObsidianCli(mock_cli_config).get_version()


def test_non_windows_does_not_require_create_no_window(
    mock_cli_config, monkeypatch
):
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout=b"1.0", stderr=b"")

    monkeypatch.setattr("second_brain.obsidian_cli.os.name", "posix")
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ObsidianCli(mock_cli_config).get_version() == "1.0"
    assert "creationflags" not in captured


def test_argument_injection_is_passed_as_single_argument(mock_dry_run_config):
    cli = ObsidianCli(config=mock_dry_run_config)
    cli.search("test; rm -rf /")
    assert "query=test; rm -rf /" in cli.operation_log[-1]["command"]
    assert cli.validate_path("../outside.md") is False


def test_note_dataclass():
    note = ObsidianNote(path="test.md", content="# Hello", vault="main")
    assert note.path == "test.md"
    assert note.content == "# Hello"
    assert note.vault == "main"
    assert ObsidianNote().tags == []


def test_vault_info_dataclass():
    info = ObsidianVaultInfo(name="test", path="/vault")
    assert info.name == "test"
    assert info.path == "/vault"


@pytest.mark.skipif(
    not ObsidianCliConfig.from_env().ok()
    or not bool(
        os.getenv("OBSIDIAN_VAULT_PATH", "")
        or os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", "")
    ),
    reason="Obsidian CLI or Vault is not configured",
)
class TestRealCli:
    def setup_method(self):
        self.cli = ObsidianCli()

    def test_version(self):
        version = self.cli.get_version()
        assert isinstance(version, str)
        assert version

    def test_vault_info(self):
        info = self.cli.get_vault_info()
        assert isinstance(info, ObsidianVaultInfo)
        assert info.name
        assert info.path

    def test_search(self):
        assert isinstance(self.cli.search("灵机", limit=5), list)

    def test_list_files(self):
        assert isinstance(self.cli.list_files(folder="PEMIS", ext=".md"), list)

    def test_health(self):
        health = self.cli.health()
        assert health["available"] is True
        assert health["cli_discovery_source"] in {
            DISCOVERY_ENVIRONMENT,
            DISCOVERY_PATH,
            DISCOVERY_PLATFORM_LOCATION,
        }

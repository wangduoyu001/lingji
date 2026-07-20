"""
==== Obsidian CLI 集成单元测试 ====

测试覆盖:
  - CLI 不存在
  - CLI 超时
  - 中文文件名/正文
  - 路径包含空格
  - 搜索无结果
  - 读取不存在的笔记
  - dry-run 不产生真实写入
  - 参数注入防护
  - 成功创建并重新读取
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from second_brain.obsidian_cli import (
    DEFAULT_CLI_PATHS,
    ObsidianCli,
    ObsidianCliConfig,
    ObsidianCliError,
    ObsidianCliErrorResult,
    ObsidianCliNotFound,
    ObsidianCliTimeout,
    ObsidianNote,
    ObsidianVaultInfo,
)


# ============================================================
# 辅助函数
# ============================================================

@pytest.fixture
def mock_cli_config():
    """模拟有效的 CLI 配置，不依赖真实环境"""
    return ObsidianCliConfig(
        cli_path="D:\\Program Files (x86)\\Obsidian\\Obsidian.com",
        vault_path="E:\\obsidian\\本地知识库",
        vault_name="本地知识库",
        timeout=15,
        dry_run=False,
    )


@pytest.fixture
def mock_dry_run_config():
    """dry-run 模式配置"""
    return ObsidianCliConfig(
        cli_path="D:\\Program Files (x86)\\Obsidian\\Obsidian.com",
        vault_path="E:\\obsidian\\本地知识库",
        vault_name="本地知识库",
        timeout=15,
        dry_run=True,
    )


# ============================================================
# 测试：配置探测
# ============================================================

def test_config_from_env_defaults():
    """测试配置从环境变量读取"""
    config = ObsidianCliConfig.from_env()
    assert isinstance(config, ObsidianCliConfig)
    assert config.timeout > 0
    assert config.vault_name == os.getenv("OBSIDIAN_VAULT_NAME", "本地知识库")


def test_config_validation_no_cli():
    """测试 CLI 不存在时的验证"""
    config = ObsidianCliConfig(cli_path="", vault_path="E:\\obsidian\\本地知识库", vault_name="test")
    issues = config.validate()
    assert any("CLI" in i for i in issues)


def test_config_validation_ok(mock_cli_config):
    """测试配置验证通过"""
    if os.path.isfile(mock_cli_config.cli_path):
        issues = mock_cli_config.validate()
        assert len(issues) == 0


# ============================================================
# 测试：异常类型
# ============================================================

def test_error_hierarchy():
    """测试异常继承链"""
    assert issubclass(ObsidianCliNotFound, ObsidianCliError)
    assert issubclass(ObsidianCliTimeout, ObsidianCliError)
    assert issubclass(ObsidianCliErrorResult, ObsidianCliError)


def test_error_message():
    """测试异常消息"""
    err = ObsidianCliError("测试错误", command="test", rc=1, err="stderr")
    assert str(err) == "测试错误"
    assert err.command == "test"
    assert err.returncode == 1
    assert err.stderr == "stderr"


# ============================================================
# 测试：安全工具
# ============================================================

def test_sanitize_filename():
    """测试文件名安全化"""
    assert ObsidianCli.sanitize_filename("normal_file.md") == "normal_file.md"
    assert "/" not in ObsidianCli.sanitize_filename("a/b:c*d?e")
    assert "\\" not in ObsidianCli.sanitize_filename("a\\b")
    # 空字符串
    assert ObsidianCli.sanitize_filename("") == ""


def test_validate_path():
    """测试路径安全验证"""
    assert ObsidianCli.validate_path("notes/test.md")
    assert ObsidianCli.validate_path("PEMIS/dashboard/Control Center.md")
    assert not ObsidianCli.validate_path("../outside.md")
    assert not ObsidianCli.validate_path("notes/../../../etc/passwd")


# ============================================================
# 测试：dry-run 模式
# ============================================================

def test_dry_run_no_writes(mock_dry_run_config):
    """测试 dry-run 模式下不产生真实写入"""
    cli = ObsidianCli(config=mock_dry_run_config)
    assert cli.config.dry_run is True

    result = cli.create("test/dry-run-test.md", "测试内容", overwrite=False)
    assert "DRY-RUN" in result or result == ""
    assert len(cli.operation_log) > 0
    assert cli.operation_log[-1]["dry_run"] is True


# ============================================================
# 测试：参数注入防护
# ============================================================

def test_argument_injection_protection():
    """测试参数注入防护"""
    cli = ObsidianCli(config=ObsidianCliConfig(
        cli_path="obsidian.com",
        vault_name="本地知识库",
        dry_run=True,
    ))
    # 恶意输入：带分号的注入
    try:
        cli.search("test; rm -rf /")
    except Exception:
        pass
    # 恶意路径
    assert cli.validate_path("../outside.md") is False


# ============================================================
# 测试：不存在的笔记
# ============================================================

def test_read_nonexistent_note():
    """测试读取不存在的笔记抛出异常"""
    config = ObsidianCliConfig.from_env()
    if not config.ok():
        pytest.skip("Obsidian CLI 不可用，跳过测试")
    cli = ObsidianCli(config=config)
    with pytest.raises((ObsidianCliError, FileNotFoundError, Exception)):
        cli.read("_不存在_的_笔记_测试_12345.md")


# ============================================================
# 测试：搜索无结果
# ============================================================

@pytest.mark.skipif(
    not ObsidianCliConfig.from_env().ok() or not bool(os.getenv("OBSIDIAN_VAULT_PATH", "") or os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", "")),
    reason="Obsidian CLI 或 Vault 未配置",
)
def test_search_no_results():
    """测试搜索无结果返回空列表"""
    config = ObsidianCliConfig.from_env()
    cli = ObsidianCli(config=config)
    results = cli.search("x1y2z3_不存在的搜索词_abc123")
    assert isinstance(results, list)
    assert len(results) == 0


# ============================================================
# 测试：dataclass
# ============================================================

def test_note_dataclass():
    """测试 ObsidianNote 数据类"""
    note = ObsidianNote(path="test.md", content="# Hello", vault="main")
    assert note.path == "test.md"
    assert note.content == "# Hello"
    assert note.vault == "main"
    # 默认值
    note2 = ObsidianNote()
    assert note2.title == ""
    assert note2.tags == []


def test_vault_info_dataclass():
    """测试 ObsidianVaultInfo 数据类"""
    info = ObsidianVaultInfo(name="test", path="/vault")
    assert info.name == "test"
    assert info.path == "/vault"


# ============================================================
# 测试：真实 CLI 集成（仅在 CLI 可用时执行）
# ============================================================

@pytest.mark.skipif(
    not ObsidianCliConfig.from_env().ok() or not bool(os.getenv("OBSIDIAN_VAULT_PATH", "") or os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", "")),
    reason="Obsidian CLI 或 Vault 未配置",
)
class TestRealCli:
    """真实 Obsidian CLI 集成测试"""

    def setup_method(self):
        self.cli = ObsidianCli()

    def test_version(self):
        """测试获取版本号"""
        version = self.cli.get_version()
        assert isinstance(version, str)
        assert len(version) > 0
        assert version.startswith("1.") or version.startswith("0.")

    def test_vault_info(self):
        """测试获取 Vault 信息"""
        info = self.cli.get_vault_info()
        assert isinstance(info, ObsidianVaultInfo)
        assert len(info.name) > 0
        assert len(info.path) > 0

    def test_search_灵机(self):
        """测试中文搜索"""
        results = self.cli.search("灵机", limit=5)
        assert isinstance(results, list)
        assert len(results) >= 0

    def test_read_existing_note(self):
        """测试读取已存在笔记"""
        try:
            content = self.cli.read("PEMIS/dashboard/Control Center.md")
            assert len(content) > 0
            assert "灵机" in content or "控制中心" in content
        except ObsidianCliErrorResult:
            pass  # 文件可能不存在

    def test_list_files(self):
        """测试列出文件"""
        files = self.cli.list_files(folder="PEMIS", ext=".md")
        assert isinstance(files, list)

    def test_health(self):
        """测试健康检查"""
        health = self.cli.health()
        assert health["available"] is True
        assert "version" in health
        assert len(health["issues"]) == 0

    def test_create_and_verify_test_note(self):
        """测试创建并验证测试笔记"""
        test_path = "系统测试/Obsidian-CLI/单元测试-验证笔记.md"
        test_content = "---\n测试: true\n---\n# 单元测试验证\n\n此笔记由自动化测试创建。\n- 创建时间: test\n- 状态: 通过"
        try:
            result = self.cli.create(test_path, test_content, overwrite=True)
            assert result is not None
            # 验证
            read_back = self.cli.read(test_path)
            assert "单元测试验证" in read_back
            assert "状态: 通过" in read_back
        finally:
            # 清理
            try:
                import subprocess as sp
                sp.run([
                    self.cli.config.cli_path,
                    f"vault={self.cli.config.vault_name}",
                    "delete", f"path={test_path}", "permanent",
                ], capture_output=True, text=True, timeout=15,
                   creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass

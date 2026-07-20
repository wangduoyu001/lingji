# -*- coding: utf-8 -*-
"""
============================================
LingJi 统一工具服务 - 单元测试
============================================

测试覆盖:
  - 统一返回格式 (tool_result)
  - Frontmatter 构建和渲染
  - 搜索、读取、创建、追加
  - Daily Note 操作
  - 任务和标签查询
  - dry-run 模式
  - 写入验证
  - 中文内容
  - 路径异常
  - CLI 不可用
  - 系统状态
  - 敏感信息过滤
  - 命令行入口
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from second_brain.obsidian_cli import (
    ObsidianCli, ObsidianCliConfig, ObsidianCliError,
    ObsidianCliErrorResult, ObsidianCliNotFound, ObsidianCliTimeout,
    ObsidianNote, ObsidianVaultInfo,
)
from second_brain.lingji_tools import (
    LingJiTools, LingJiToolsConfig,
    build_frontmatter, render_frontmatter, tool_result,
    MAX_BATCH_SIZE, DEFAULT_SEARCH_LIMIT, DEFAULT_TASK_LIMIT, DEFAULT_TAG_LIMIT,
)

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_cli():
    """模拟 ObsidianCli，避免真实依赖"""
    mock = MagicMock(spec=ObsidianCli)

    # 配置 health() 返回
    health_result = {
        "available": True,
        "version": "1.5.3",
        "vault_name": "测试库",
        "vault_path": "E:\\test\\obsidian",
        "cli_path": "D:\\Obsidian.com",
        "issues": [],
        "dry_run": False,
    }
    mock.health.return_value = health_result

    # 配置 search
    mock.search.return_value = [
        "笔记1.md", "笔记2.md", "测试/灵机笔记.md"
    ]

    # 配置 read
    mock.read.return_value = "# 测试笔记\n\n这是测试内容。\n\n## AI 相关\n\n灵机正在工作。\n"

    # 配置 get_vault_info
    info = ObsidianVaultInfo(name="测试库", path="E:\\test\\obsidian",
                             file_count=100, folder_count=10, size="1.2 MB")
    mock.get_vault_info.return_value = info

    # 配置 list_tasks
    mock.list_tasks.return_value = [
        "- [ ] 任务1",
        "- [ ] 任务2",
        "- [x] 已完成任务",
    ]

    # 配置 list_tags
    mock.list_tags.return_value = ["AI", "灵机", "测试", "PEMIS"]

    # 配置 create
    mock.create.return_value = "created"

    # 配置 append
    mock.append.return_value = "appended"

    # 配置 append_daily
    mock.append_daily.return_value = "appended to daily"

    # 配置 get_daily_path
    mock.get_daily_path.return_value = "Daily/2025-01-15.md"

    # 配置 config
    config = ObsidianCliConfig(
        cli_path="D:\\Obsidian.com",
        vault_path="E:\\test\\obsidian",
        vault_name="测试库",
        timeout=15,
        dry_run=False,
    )
    mock.config = config

    return mock


@pytest.fixture
def tools(mock_cli):
    """使用 mock 的 LingJiTools 实例"""
    config = LingJiToolsConfig(dry_run=False, task_id="test-task-001")
    return LingJiTools(obsidian_cli=mock_cli, config=config)


@pytest.fixture
def dry_run_tools(mock_cli):
    """dry-run 模式"""
    config = LingJiToolsConfig(dry_run=True, task_id="test-dry-run")
    return LingJiTools(obsidian_cli=mock_cli, config=config)


@pytest.fixture
def broken_cli():
    """模拟不可用的 CLI"""
    mock = MagicMock(spec=ObsidianCli)
    health = {
        "available": False, "version": "未知",
        "vault_name": "", "vault_path": "", "cli_path": "",
        "issues": ["CLI 未找到", "Vault 路径不存在"],
        "dry_run": False,
    }
    mock.health.return_value = health
    config = ObsidianCliConfig(cli_path="", vault_path="", vault_name="", timeout=5, dry_run=False)
    mock.config = config
    return mock


@pytest.fixture
def broken_tools(broken_cli):
    """CLI 不可用时的工具实例"""
    return LingJiTools(obsidian_cli=broken_cli)

# ============================================================
# 测试：统一返回格式
# ============================================================

def test_tool_result_success():
    """测试成功返回格式"""
    r = tool_result(True, {"key": "value"}, None, "test", 10.5, "t1")
    assert r["ok"] is True
    assert r["data"]["key"] == "value"
    assert r["error"] is None
    assert r["meta"]["tool"] == "test"
    assert r["meta"]["duration_ms"] == 10.5
    assert r["meta"]["task_id"] == "t1"
    assert "timestamp" in r["meta"]


def test_tool_result_failure():
    """测试失败返回格式"""
    r = tool_result(False, error="错误信息", tool="fail")
    assert r["ok"] is False
    assert r["data"] == {}
    assert r["error"] == "错误信息"
    assert r["meta"]["tool"] == "fail"


def test_tool_result_defaults():
    """测试返回值"""
    r = tool_result(True)
    assert r["ok"] is True
    assert r["data"] == {}
    assert r["error"] is None
    assert r["meta"]["duration_ms"] == 0


# ============================================================
# 测试：Frontmatter
# ============================================================

def test_build_frontmatter_basic():
    """测试基本 Frontmatter"""
    fm = build_frontmatter("测试标题", tags=["tag1", "tag2"])
    assert fm["title"] == "测试标题"
    assert "tag1" in fm["tags"]
    assert fm["status"] == "draft"
    assert fm["created"]


def test_build_frontmatter_custom():
    """测试自定义 Frontmatter"""
    fm = build_frontmatter("知识条目", source="test", source_type="knowledge",
                           tags=["AI"], task_id="t1", status="published", indexed=True)
    assert fm["source_type"] == "knowledge"
    assert fm["task_id"] == "t1"
    assert fm["status"] == "published"
    assert fm["indexed"] is True


def test_render_frontmatter():
    """测试 Frontmatter 渲染"""
    fm = build_frontmatter("标题", tags=["tag1", "tag2"])
    rendered = render_frontmatter(fm)
    assert rendered.startswith("---")
    assert rendered.endswith("---")
    assert "title: 标题" in rendered
    assert "tags: [tag1, tag2]" in rendered


def test_render_frontmatter_no_tags():
    """测试无标签 Frontmatter 渲染"""
    fm = build_frontmatter("无标签")
    rendered = render_frontmatter(fm)
    assert "tags: []" in rendered


# ============================================================
# 测试：搜索
# ============================================================

def test_search_notes(tools):
    """测试搜索"""
    result = tools.search_notes("灵机", limit=5)
    assert result["ok"] is True
    assert result["meta"]["tool"] == "search_notes"
    assert "notes" in result["data"]
    assert result["data"]["total"] >= 0


def test_search_no_results(tools):
    """测试无结果搜索"""
    tools.obsidian.search.return_value = []
    result = tools.search_notes("不存在的关键词_xyz")
    assert result["ok"] is True
    assert result["data"]["notes"] == []
    assert result["data"]["total"] == 0


# ============================================================
# 测试：读取
# ============================================================

def test_read_note(tools):
    """测试读取笔记"""
    result = tools.read_note("test.md")
    assert result["ok"] is True
    assert "content" in result["data"]
    assert result["data"]["path"] == "test.md"


def test_read_note_cli_error(tools):
    """测试读取时 CLI 错误"""
    tools.obsidian.read.side_effect = ObsidianCliError("文件不存在")
    result = tools.read_note("不存在.md")
    assert result["ok"] is False
    assert "不存在" in result["error"]


# ============================================================
# 测试：创建
# ============================================================

def test_create_note(tools):
    """测试创建笔记"""
    result = tools.create_note("test/新笔记.md", "这是内容", metadata={"tags": ["test"]})
    assert result["ok"] is True
    assert result["data"]["path"] == "test/新笔记.md"
    assert result["data"]["verified"] is True


def test_create_note_dry_run(dry_run_tools):
    """测试 dry-run 不真实创建"""
    result = dry_run_tools.create_note("test/dry.md", "内容", metadata={"tags": ["test"]})
    assert result["ok"] is True
    assert result["data"]["dry_run"] is True


# ============================================================
# 测试：追加
# ============================================================

def test_append_note(tools):
    """测试追加内容"""
    result = tools.append_note("test/现有笔记.md", "\n追加的内容")
    assert result["ok"] is True
    assert result["data"]["verified"] is True


def test_append_note_dry_run(dry_run_tools):
    """测试 dry-run 不真实追加"""
    result = dry_run_tools.append_note("test/笔记.md", "内容")
    assert result["ok"] is True
    assert result["data"]["dry_run"] is True


# ============================================================
# 测试：Daily Note
# ============================================================

def test_append_daily(tools):
    """测试追加到 Daily Note"""
    result = tools.append_daily("- 测试内容")
    assert result["ok"] is True
    assert "daily_path" in result["data"]


def test_append_daily_dry_run(dry_run_tools):
    """测试 dry-run Daily Note"""
    result = dry_run_tools.append_daily("- 内容")
    assert result["ok"] is True
    assert result["data"]["dry_run"] is True


# ============================================================
# 测试：任务和标签
# ============================================================

def test_list_tasks(tools):
    """测试列出任务"""
    result = tools.list_tasks()
    assert result["ok"] is True
    assert "tasks" in result["data"]
    assert result["data"]["total"] >= 0


def test_list_tasks_todo(tools):
    """测试列出未完成任务"""
    result = tools.list_tasks(status="todo")
    assert result["ok"] is True


def test_list_tags(tools):
    """测试列出标签"""
    result = tools.list_tags()
    assert result["ok"] is True
    assert "tags" in result["data"]


# ============================================================
# 测试：Vault 信息
# ============================================================

def test_get_vault_info(tools):
    """测试获取 Vault 信息"""
    result = tools.get_vault_info()
    assert result["ok"] is True
    assert result["data"]["name"] == "测试库"
    assert result["data"]["file_count"] == 100


# ============================================================
# 测试：CLI 不可用
# ============================================================

def test_cli_not_available(broken_tools):
    """测试 CLI 不可用时的所有操作返回错误"""
    for method in ["search_notes", "read_note", "create_note", "append_note",
                    "append_daily", "list_tasks", "list_tags", "get_vault_info"]:
        result = getattr(broken_tools, method)(
            *(["测试"] if method in ("search_notes",) else []),
            **( {"path": "test.md"} if method == "read_note" else
                {"path": "test.md", "content": "x"} if method == "create_note" else
                {"path": "test.md", "content": "x"} if method == "append_note" else
                {"content": "x"} if method == "append_daily" else {} )
        )
        assert not result.get("dry_run", False)  # dry_run guard not triggered
        assert result["ok"] is False
        assert "不可用" in result["error"]


# ============================================================
# 测试：健康检查
# ============================================================

def test_health_check(tools):
    """测试健康检查"""
    result = tools.health_check()
    assert result["ok"] is True
    assert result["data"]["cli_available"] is True
    assert result["data"]["version"] == "1.5.3"


def test_health_check_broken(broken_tools):
    """测试 CLI 不可用时的健康检查"""
    result = broken_tools.health_check()
    assert result["ok"] is True  # health_check 本身不会失败
    assert result["data"]["cli_available"] is False
    assert len(result["data"]["issues"]) > 0


# ============================================================
# 测试：系统状态
# ============================================================

def test_get_system_status(tools):
    """测试系统状态"""
    result = tools.get_system_status()
    assert result["ok"] is True
    assert result["data"]["status"] == "ok"
    assert "cli" in result["data"]
    assert "vault" in result["data"]
    assert "tool_layer" in result["data"]


def test_get_system_status_broken(broken_tools):
    """测试 CLI 不可用时的系统状态"""
    result = broken_tools.get_system_status()
    assert result["ok"] is True
    assert result["data"]["status"] == "degraded"


# ============================================================
# 测试：知识条目创建
# ============================================================

def test_create_knowledge_entry(tools):
    """测试创建知识条目"""
    tools.obsidian.create.return_value = "created"
    result = tools.create_knowledge_entry("测试知识", "这是内容", tags=["AI"])
    assert result["ok"] is True
    assert result["data"]["title"] == "测试知识"
    assert result["data"]["verified"] is True
    # 验证路径包含知识库
    assert "知识库" in result["data"]["path"]


def test_create_knowledge_entry_dry_run(dry_run_tools):
    """测试 dry-run 创建知识条目"""
    result = dry_run_tools.create_knowledge_entry("标题", "内容")
    assert result["ok"] is True
    assert result["data"]["dry_run"] is True


# ============================================================
# 测试：AI 新闻条目创建
# ============================================================

def test_create_ai_news_entry(tools):
    """测试创建 AI 新闻条目"""
    result = tools.create_ai_news_entry("AI 突破", "摘要", source_url="https://example.com")
    assert result["ok"] is True
    assert result["data"]["verified"] is True
    assert "AI新闻" in result["data"]["path"]


# ============================================================
# 测试：机会条目创建
# ============================================================

def test_create_opportunity_entry(tools):
    """测试创建机会条目"""
    result = tools.create_opportunity_entry("新机会", "摘要", score=7.5)
    assert result["ok"] is True
    assert result["data"]["score"] == 7.5
    assert "opportunity" in result["data"]["path"] or "PEMIS" in result["data"]["path"]


def test_create_opportunity_entry_score_clamp(tools):
    """测试评分的上下界限制"""
    r1 = tools.create_opportunity_entry("低分", "内容", score=-5)
    assert r1["ok"] is True
    assert r1["data"]["score"] == 0.0

    r2 = tools.create_opportunity_entry("高分", "内容", score=50)
    assert r2["ok"] is True
    assert r2["data"]["score"] == 10.0


# ============================================================
# 测试：操作日志
# ============================================================

def test_operation_log(tools):
    """测试操作日志记录"""
    # 执行几个操作
    tools.search_notes("测试")
    tools.list_tags()
    result = tools.get_operation_log()
    assert result["ok"] is True
    assert result["data"]["total"] >= 2
    assert len(result["data"]["logs"]) >= 2


# ============================================================
# 测试：配置
# ============================================================

def test_config_from_env(monkeypatch):
    """测试从环境变量加载配置"""
    monkeypatch.setenv("LINGJI_TOOLS_DRY_RUN", "1")
    cfg = LingJiToolsConfig.from_env()
    assert cfg.dry_run is True
    monkeypatch.delenv("LINGJI_TOOLS_DRY_RUN", raising=False)

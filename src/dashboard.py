import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pemis.dashboard")

OPP_VAULT_DIR = "04-Projects/Money-Experiments/Opportunities"
DASH_VAULT_DIR = "00-System/Dashboard"


def sync_opps_to_vault(core):
    """Sync generated opportunity cards into the single Obsidian vault."""
    source_dir = core.settings.storage_path / "opportunities"
    target_dir = core.settings.vault_path / OPP_VAULT_DIR
    if not source_dir.exists():
        logger.warning("Source opportunity dir not found: %s", source_dir)
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    removed = 0
    for source_file in source_dir.glob("*.md"):
        try:
            shutil.copy2(source_file, target_dir / source_file.name)
            copied += 1
        except Exception as exc:
            logger.error("Copy error %s: %s", source_file.name, exc)
    target_files = {path.name for path in target_dir.glob("*.md")}
    source_files = {path.name for path in source_dir.glob("*.md")}
    for name in target_files - source_files:
        try:
            (target_dir / name).unlink()
            removed += 1
        except Exception:
            pass
    if copied or removed:
        logger.info("Synced opportunities: %d copied, %d removed", copied, removed)


def get_opp_filename(core, opp_id):
    opp_dir = core.settings.storage_path / "opportunities"
    if not opp_dir.exists():
        return ""
    for source_file in opp_dir.glob("*.md"):
        try:
            text = source_file.read_text(encoding="utf-8-sig")
            if "id: " + repr(opp_id) in text or str(opp_id) in text[:500]:
                return source_file.name
        except Exception:
            pass
    return ""


def update_dashboard(core):
    """Write a display-only control center; owner input lives in separate notes."""
    sync_opps_to_vault(core)
    decisions = core.decision.get_latest()
    now = datetime.now()
    status = core.status() if hasattr(core, "status") else {}

    mode = status.get("mode", "NORMAL")
    uptime = status.get("uptime", "刚刚启动")
    entries = status.get("index_entries", 0)
    feedback_time = status.get("feedback_read")
    feedback_text = feedback_time.strftime("%H:%M") if feedback_time else "-"
    layout = status.get("vault_layout", {})
    layout_text = "完整" if layout.get("complete") else "未完成"
    commands = status.get("manual_commands", {})
    jobs = status.get("jobs", [])
    failed_jobs = sum(1 for job in jobs if job.get("status") == "failed")
    memory_index = status.get("memory_index", {})
    memory_integrity = status.get("memory_integrity", {})
    memory_health = "正常" if memory_integrity.get("healthy") else "异常"

    lines = [
        "---",
        "schema_version: 1",
        "memory_type: dashboard",
        "status: active",
        "privacy: private",
        "lingji_managed: true",
        "updated_at: " + now.isoformat(timespec="seconds"),
        "---",
        "",
        "# 灵机控制中心",
        "",
        "> 只负责展示。反馈、命令和正式内容分别写入独立文件，不在这里直接编辑。",
        "",
        "## 系统状态",
        "",
        f"- 模式：**{mode}**",
        f"- 运行时间：{uptime}",
        f"- 元数据索引：{entries} 条",
        f"- 召回库：{memory_index.get('documents', 0)} 份文档 / {memory_index.get('chunks', 0)} 个分块",
        f"- 核心记忆：{memory_index.get('core_memories', 0)} 条",
        f"- 召回版本：{memory_index.get('revision', 0)}",
        f"- FTS 分词：{memory_index.get('fts_tokenizer', '-')}",
        f"- 召回健康：**{memory_health}**",
        f"- 单仓库结构：{layout_text}",
        f"- 调度失败：{failed_jobs}",
        f"- 反馈最近读取：{feedback_text}",
        f"- 命令：排队 {commands.get('queued', 0)} / 执行中 {commands.get('running', 0)} / 失败 {commands.get('failed', 0)}",
        "",
        "## 手动管理入口",
        "",
        "- [[00-System/Home|灵机管理首页]]",
        "- [[00-System/Permanent-Memory|永久记忆中心]]",
        "- [[00-System/Feedback/Feedback Inbox|填写反馈]]",
        "- [[00-System/Bases/Inbox.base|管理收件箱]]",
        "- [[00-System/Bases/Projects.base|管理项目]]",
        "- [[00-System/Bases/Tasks.base|管理任务]]",
        "- [[00-System/Bases/Commands.base|查看命令队列]]",
        "- [[00-System/Bases/Memory Health.base|检查记忆健康]]",
        "",
        "---",
        "",
    ]

    if not memory_integrity.get("healthy", True):
        lines.extend(
            [
                "## 召回异常",
                "",
                f"- SQLite 检查：{memory_integrity.get('quick_check', '-')}",
                f"- 孤立分块：{memory_integrity.get('orphan_chunks', 0)}",
                f"- FTS 行数：{memory_integrity.get('fts_rows', 0)}",
                f"- 分块行数：{memory_integrity.get('chunk_rows', 0)}",
                "",
                "> 后台完整性任务会尝试自动重建召回库。正式记忆仍保存在 Obsidian，不会因索引损坏而丢失。",
                "",
                "---",
                "",
            ]
        )

    output = decisions.get("decisions", [])
    lines.extend(["## 今天最值得关注的3个机会", ""])
    if output:
        for index, decision in enumerate(output[:3], 1):
            title = decision["title"][:40]
            score = decision["decision_score"]
            speed_icon = (
                "⚡"
                if decision.get("speed") == "fast"
                else "🐢"
                if decision.get("speed") == "slow"
                else "➡️"
            )
            lines.append(f"{index}. {speed_icon} **{title}**（评分 {score}）")
            opp_filename = get_opp_filename(core, decision["id"])
            if opp_filename:
                target = OPP_VAULT_DIR + "/" + opp_filename
                lines.append("   [[" + target.replace(".md", "") + "|查看详情 →]]")
            lines.append("")
    else:
        lines.extend(["*暂无有效机会。*", ""])

    preferences_path = Path(core.settings.storage_path) / "user_preferences.json"
    lines.extend(["---", "", "## 最近反馈", ""])
    if preferences_path.exists():
        try:
            preferences = json.loads(preferences_path.read_text(encoding="utf-8-sig"))
            records = []
            label_map = {
                "liked": "👍",
                "disliked": "👎",
                "executed": "✅",
                "failed": "❌",
                "new_ideas": "💡",
            }
            for key in ("liked", "disliked", "executed", "failed", "new_ideas"):
                items = preferences.get(key, [])
                if items:
                    records.append(label_map[key] + " " + items[-1].get("content", "")[:80])
            if records:
                lines.extend("- " + record for record in records[-5:])
            else:
                lines.append("*暂无反馈。*")
        except Exception:
            lines.append("*反馈状态读取失败，请查看日志。*")
    else:
        lines.append("*暂无反馈。*")

    lines.extend(["", "---", "", f"> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}", ""])

    dashboard_dir = core.settings.vault_path / DASH_VAULT_DIR
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = dashboard_dir / "Control Center.md"
    temp_file = dashboard_file.with_suffix(".md.tmp")
    temp_file.write_text("\n".join(lines), encoding="utf-8")
    temp_file.replace(dashboard_file)
    logger.info("Control Center updated: %s", dashboard_file)

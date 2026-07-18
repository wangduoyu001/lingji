import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pemis.dashboard")

# Qdrant remains optional. The single-vault folders and metadata are the stable layer.
OPP_VAULT_DIR = "04-Projects/Money-Experiments/Opportunities"
DASH_VAULT_DIR = "00-System/Dashboard"
LEGACY_OPP_VAULT_DIR = "PEMIS/opportunities"
LEGACY_DASH_VAULT_DIR = "PEMIS/dashboard"


def sync_opps_to_vault(core):
    """Sync generated opportunity cards into the single Obsidian vault."""
    source_dir = core.settings.storage_path / "opportunities"
    target_dir = core.settings.vault_path / OPP_VAULT_DIR
    if not source_dir.exists():
        logger.warning("Source opp dir not found: %s", source_dir)
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


def load_opp_summary(core, file_id):
    opp_dir = core.settings.storage_path / "opportunities"
    if not opp_dir.exists():
        return "", ""
    for source_file in opp_dir.glob("*.md"):
        try:
            text = source_file.read_text(encoding="utf-8-sig")
            if "id: " + repr(file_id) in text or file_id in text[:200]:
                title = ""
                for line in text.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                body = text.strip()
                if body.startswith("---"):
                    end = body.find("---", 3)
                    if end != -1:
                        body = body[end + 3 :].strip()
                summary_lines = []
                found_title = False
                for line in body.splitlines():
                    if line.startswith("# "):
                        found_title = True
                        continue
                    if found_title and line.strip() and not line.startswith("**Score"):
                        summary_lines.append(line.strip())
                        if len("".join(summary_lines)) > 200:
                            break
                return title, " ".join(summary_lines)[:300]
        except Exception:
            pass
    return "", ""


def get_opp_filename(core, opp_id):
    opp_dir = core.settings.storage_path / "opportunities"
    if not opp_dir.exists():
        return ""
    for source_file in opp_dir.glob("*.md"):
        try:
            text = source_file.read_text(encoding="utf-8-sig")
            if "id: " + repr(opp_id) in text or opp_id in text[:200]:
                return source_file.name
        except Exception:
            pass
    return ""


def update_dashboard(core):
    """Write the real control center into 00-System/Dashboard."""
    sync_opps_to_vault(core)
    decisions = core.decision.get_latest()
    now = datetime.now()
    status = core.status() if hasattr(core, "status") else {}

    lines = [
        "---",
        "schema_version: 1",
        "memory_type: dashboard",
        "status: active",
        "privacy: private",
        "updated_at: " + now.isoformat(),
        "---",
        "",
        "# 灵机控制中心",
        "",
        "> 更新时间: " + now.strftime("%Y-%m-%d %H:%M"),
        "",
        "---",
        "",
    ]

    mode = status.get("mode", "NORMAL")
    uptime = status.get("uptime", "刚刚启动")
    entries = status.get("index_entries", 0)
    feedback_time = status.get("feedback_read")
    feedback_text = feedback_time.strftime("%H:%M") if feedback_time else "-"
    layout = status.get("vault_layout", {})
    layout_text = "完整" if layout.get("complete") else "未完成"
    lines.append(
        "🟢 **"
        + str(mode)
        + "** | 运行 "
        + str(uptime)
        + " | 索引 "
        + str(entries)
        + " 条 | 单仓库结构: "
        + layout_text
        + " | 反馈读取: "
        + feedback_text
    )
    lines.append("")

    output = decisions.get("decisions", [])
    if output:
        lines.extend(["**💰 今天最值得做的3件事**", ""])
        for index, decision in enumerate(output[:3], 1):
            title = decision["title"][:25]
            score = str(decision["decision_score"])
            speed_icon = "⚡" if decision.get("speed") == "fast" else "🐢" if decision.get("speed") == "slow" else "➡️"
            lines.append(f"{index}. {speed_icon} **{title}**  (评分 {score})")
            opp_filename = get_opp_filename(core, decision["id"])
            if opp_filename:
                target = OPP_VAULT_DIR + "/" + opp_filename
                lines.append("   [[" + target.replace(".md", "") + "|查看详情 →]]")
            lines.append("")
    else:
        lines.extend(["*暂无决策*", ""])

    lines.extend(
        [
            "---",
            "",
            "**📝 反馈与备注**",
            "",
            "- 喜欢/感兴趣: ",
            "- 不感兴趣/放弃: ",
            "- 已开始执行: ",
            "- 我想到的新方向: ",
            "",
            "*(填好后保存，灵机自动读取)*",
            "",
            "---",
            "",
        ]
    )

    preferences_path = Path(core.settings.storage_path) / "user_preferences.json"
    if preferences_path.exists():
        try:
            preferences = json.loads(preferences_path.read_text(encoding="utf-8-sig"))
            records = []
            for key in ("liked", "disliked", "executed", "failed"):
                items = preferences.get(key, [])
                if items:
                    label_map = {"liked": "👍", "disliked": "👎", "executed": "✅", "failed": "❌"}
                    records.append(label_map.get(key, key) + " " + items[-1].get("content", "")[:50])
            if records:
                lines.extend(["**最近反馈:**", ""])
                lines.extend("- " + record for record in records[-3:])
                lines.extend(["", "---", ""])
        except Exception:
            pass

    dashboard_dir = core.settings.vault_path / DASH_VAULT_DIR
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = dashboard_dir / "Control Center.md"
    temp_file = dashboard_file.with_suffix(".md.tmp")
    temp_file.write_text("\n".join(lines), encoding="utf-8")
    temp_file.replace(dashboard_file)
    logger.info("Control Center updated: %s", dashboard_file)

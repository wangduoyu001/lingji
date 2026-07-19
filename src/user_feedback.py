"""Read append-only owner feedback without rewriting the dashboard."""
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger("pemis.feedback")

FEEDBACK_TEMPLATE = """---
memory_type: feedback_inbox
status: active
privacy: private
---

# 反馈收件箱

> 直接修改下面内容并保存。控制中心只负责展示，不会覆盖这里。

- 喜欢/感兴趣: 
- 不感兴趣/放弃: 
- 已开始执行: 
- 失败的: 
- 我想到的新方向: 

## 针对机会的反馈

可按下面格式追加：

### 1. 机会标题
- 感兴趣程度: 
- 我能做吗: 
- 什么时候执行: 
"""


class UserFeedback:
    def __init__(self, settings):
        self.settings = settings
        self.feedback_path = settings.storage_path / "user_preferences.json"
        self.feedback_inbox = (
            settings.vault_path / "00-System" / "Feedback" / "Feedback Inbox.md"
        )
        self._ensure_feedback_inbox()
        self._prefs = self._load()
        self._prefs.setdefault("liked", [])
        self._prefs.setdefault("disliked", [])
        self._prefs.setdefault("executed", [])
        self._prefs.setdefault("failed", [])
        self._prefs.setdefault("new_ideas", [])
        self._prefs.setdefault("per_opportunity", [])
        self._prefs.setdefault("weight_adjustments", {})

    def _ensure_feedback_inbox(self):
        self.feedback_inbox.parent.mkdir(parents=True, exist_ok=True)
        if not self.feedback_inbox.exists():
            self.feedback_inbox.write_text(FEEDBACK_TEMPLATE, encoding="utf-8")

    def _load(self):
        if self.feedback_path.exists():
            try:
                with open(self.feedback_path, "r", encoding="utf-8-sig") as handle:
                    return json.load(handle)
            except Exception as exc:
                logger.warning("Unable to load feedback state: %s", exc)
        return {}

    def _save(self):
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.feedback_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self._prefs, handle, ensure_ascii=False, indent=2)
        temp_path.replace(self.feedback_path)

    def read_from_control_center(self):
        """Compatibility method; feedback now lives in its own owner-controlled note."""
        return self.read_feedback_inbox()

    def read_feedback_inbox(self):
        self._ensure_feedback_inbox()
        text = self.feedback_inbox.read_text(encoding="utf-8-sig")
        changed = False
        patterns = {
            "liked": r"(?:喜欢/感兴趣|喜欢的机会)[：:]\s*(.+)",
            "disliked": r"(?:不感兴趣/放弃|不感兴趣的)[：:]\s*(.+)",
            "executed": r"(?:已开始执行|已执行的)[：:]\s*(.+)",
            "failed": r"失败的[：:]\s*(.+)",
            "new_ideas": r"(?:我想到的新方向|新想法)[：:]\s*(.+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if not match:
                continue
            value = match.group(1).strip()
            if not value or value in {"-", "无", "暂无"}:
                continue
            existing = [item.get("content") for item in self._prefs[key] if isinstance(item, dict)]
            if value not in existing:
                self._prefs[key].append(
                    {"content": value, "timestamp": datetime.now().isoformat(timespec="seconds")}
                )
                changed = True
                logger.info("Feedback recorded: %s = %s", key, value[:50])

        opp_sections = re.findall(r"### \d+\.\s*(.+?)(?=###|\Z)", text, re.DOTALL)
        for section in opp_sections:
            lines = section.strip().split("\n")
            title = lines[0].strip() if lines else ""
            interest = ""
            can_do = ""
            timing = ""
            for line in lines:
                if "感兴趣程度" in line:
                    interest = line.split(":")[-1].strip()
                elif "我能做吗" in line:
                    can_do = line.split(":")[-1].strip()
                elif "什么时候执行" in line:
                    timing = line.split(":")[-1].strip()
            if not (interest or can_do or timing):
                continue
            signature = (title[:60], interest, can_do, timing)
            existing = {
                (
                    item.get("title", ""),
                    item.get("interest", ""),
                    item.get("can_do", ""),
                    item.get("timing", ""),
                )
                for item in self._prefs["per_opportunity"]
            }
            if signature not in existing:
                self._prefs["per_opportunity"].append(
                    {
                        "title": title[:60],
                        "interest": interest,
                        "can_do": can_do,
                        "timing": timing,
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                changed = True

        if changed:
            self._save()
        return {"changed": changed, "path": str(self.feedback_inbox)}

    def get_weight_adjustment(self, monetization_type):
        return self._prefs.get("weight_adjustments", {}).get(monetization_type, 1.0)

    def get_preferences(self):
        return self._prefs

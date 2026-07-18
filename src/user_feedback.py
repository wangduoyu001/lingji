"""Read feedback from the single-vault Control Center and adjust preferences."""
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger("pemis.feedback")


class UserFeedback:
    def __init__(self, settings):
        self.settings = settings
        self.feedback_path = settings.storage_path / "user_preferences.json"
        self._prefs = self._load()
        self._prefs.setdefault("liked", [])
        self._prefs.setdefault("disliked", [])
        self._prefs.setdefault("executed", [])
        self._prefs.setdefault("failed", [])
        self._prefs.setdefault("weight_adjustments", {})

    def _load(self):
        if self.feedback_path.exists():
            try:
                with open(self.feedback_path, "r", encoding="utf-8-sig") as handle:
                    return json.load(handle)
            except Exception:
                pass
        return {}

    def _save(self):
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.feedback_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self._prefs, handle, ensure_ascii=False, indent=2)
        temp_path.replace(self.feedback_path)

    def _control_center_path(self):
        current = self.settings.vault_path / "00-System" / "Dashboard" / "Control Center.md"
        if current.exists():
            return current
        return self.settings.vault_path / "PEMIS" / "dashboard" / "Control Center.md"

    def read_from_control_center(self):
        control_center = self._control_center_path()
        if not control_center.exists():
            return

        text = control_center.read_text(encoding="utf-8-sig")
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
            self._prefs.setdefault(key, [])
            existing = [item.get("content") for item in self._prefs[key] if isinstance(item, dict)]
            if value not in existing:
                self._prefs[key].append({"content": value, "timestamp": datetime.now().isoformat()})
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
            if interest or can_do or timing:
                entry = {
                    "title": title[:60],
                    "interest": interest,
                    "can_do": can_do,
                    "timing": timing,
                    "timestamp": datetime.now().isoformat(),
                }
                self._prefs.setdefault("per_opportunity", [])
                existing_titles = [item.get("title", "") for item in self._prefs["per_opportunity"]]
                if title[:60] not in existing_titles:
                    self._prefs["per_opportunity"].append(entry)
                    changed = True

        if changed:
            self._save()

    def get_weight_adjustment(self, monetization_type):
        return self._prefs.get("weight_adjustments", {}).get(monetization_type, 1.0)

    def get_preferences(self):
        return self._prefs

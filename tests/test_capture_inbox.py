"""手机捕获收件箱 watcher：解析/分发/归档全流程。"""

from __future__ import annotations

from pathlib import Path

from src.control.capture_inbox import CaptureInboxWatcher, resolve_inbox_dir


def _watcher(tmp_path: Path, submitted: list[dict]) -> CaptureInboxWatcher:
    inbox = tmp_path / "LingJiInbox"
    inbox.mkdir(parents=True)
    return CaptureInboxWatcher(submit=submitted.append, inbox_dir=inbox, poll_seconds=3600)


def test_json_entry_is_parsed_submitted_and_archived(tmp_path: Path):
    submitted: list[dict] = []
    watcher = _watcher(tmp_path, submitted)
    entry = tmp_path / "LingJiInbox" / "a.json"
    entry.write_text(
        '{"text": "讲的曝光三角很清楚", "url": "https://v.douyin.com/x", "source_app": "douyin"}',
        encoding="utf-8",
    )
    result = watcher.scan_once()
    assert result == {"processed": 1, "failed": 0}
    assert len(submitted) == 1
    payload = submitted[0]
    assert "曝光三角" in payload["text"]
    assert payload["url"] == "https://v.douyin.com/x"
    assert payload["platform"] == "douyin"
    assert not entry.exists()
    assert list((tmp_path / "LingJiInbox" / "processed").glob("*a.json"))


def test_plain_text_entry_defaults_to_mobile_share(tmp_path: Path):
    submitted: list[dict] = []
    watcher = _watcher(tmp_path, submitted)
    (tmp_path / "LingJiInbox" / "note.txt").write_text("一段纯文本笔记", encoding="utf-8")
    watcher.scan_once()
    assert submitted[0]["text"] == "一段纯文本笔记"
    assert submitted[0]["platform"] == "mobile_share"


def test_broken_json_goes_to_failed_not_silent(tmp_path: Path):
    submitted: list[dict] = []
    watcher = _watcher(tmp_path, submitted)
    bad = tmp_path / "LingJiInbox" / "broken.json"
    bad.write_text("{ 不是json", encoding="utf-8")
    empty = tmp_path / "LingJiInbox" / "empty.txt"
    empty.write_text("   ", encoding="utf-8")
    result = watcher.scan_once()
    assert result["failed"] == 2 and result["processed"] == 0
    assert submitted == []
    assert len(list((tmp_path / "LingJiInbox" / "failed").glob("*"))) == 2


def test_resolve_inbox_prefers_icloud_when_present(tmp_path: Path, monkeypatch):
    import src.control.capture_inbox as module

    icloud = tmp_path / "CloudDocs"
    icloud.mkdir()
    monkeypatch.setattr(module, "_ICLOUD_CONTAINER", str(icloud))
    resolved = module.resolve_inbox_dir()
    assert resolved == icloud / "LingJiInbox"
    fallback = Path(str(tmp_path / "no-such-home")) / "x"
    monkeypatch.setattr(module, "_ICLOUD_CONTAINER", str(fallback / "Mobile Documents" / "com~apple~CloudDocs"))
    assert module.resolve_inbox_dir() == Path.home() / "LingJiInbox"
    assert resolve_inbox_dir() is not None

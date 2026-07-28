from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.control.drama_api import register_drama_routes
from src.plugins.drama_intelligence import DramaService, ScannedPdfRequiresOcr, load_script


def _settings(tmp_path: Path) -> SimpleNamespace:
    root = tmp_path.resolve()
    storage = root / "acceptance" / "storage"
    return SimpleNamespace(
        storage_path=storage,
        workspace_name="acceptance",
        workspace_root=root,
        acceptance_storage_dir=storage,
        acceptance_raw_dir=root / "acceptance" / "raw",
        acceptance_qdrant_mode="memory",
        acceptance_qdrant_collection="lingji_memory_acceptance",
        qdrant_distance="cosine",
        qdrant_timeout_seconds=1.0,
        embedding_enabled=False,
        state_db_name="lingji_state.db",
        memory_db_name="lingji_memory.db",
        runtime_settings_file="runtime_settings.json",
    )


def _sample_script() -> str:
    return """人物简介：林晚隐藏了集团继承人身份。

第1集 被羞辱
第一场
林晚：我只是来送文件。
赵明：保洁也配进董事会？
旁白：众人哄笑，林晚保持沉默。

第二场
董事长：请大小姐上座。
赵明：什么？她是真正的继承人？
林晚：现在可以谈合同了吗？

第2集 新危机
第一场
赵明：我不会就这样认输。
林晚：你伪造合同的证据已经提交。
"""


def test_import_parse_trace_and_hybrid_lexical_fallback(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text(_sample_script(), encoding="utf-8")
    service = DramaService(_settings(tmp_path), runtime_values={"embedding_enabled": False})

    imported = service.import_script(str(source))
    drama = imported["drama"]
    assert imported["duplicate"] is False
    assert drama["episode_count"] == 2
    assert drama["scene_count"] == 3
    assert drama["character_count"] >= 3
    assert Path(drama["raw_path"]).is_file()
    assert Path(drama["normalized_path"]).is_file()

    search = service.search("继承人", limit=5)
    assert search["results"]
    result = search["results"][0]
    assert result["source_ref"].startswith(drama["drama_id"] + ":e001")
    assert result["start_offset"] < result["end_offset"]
    assert "继承人" in result["text"]
    assert "关键词或原文命中" in result["match_reasons"]

    duplicate = service.import_script(str(source))
    assert duplicate["duplicate"] is True
    assert service.status()["structured"]["dramas"] == 1


def test_import_fifty_thousand_character_script(tmp_path: Path) -> None:
    source = tmp_path / "long.md"
    body = "第1集\n第一场\n林晚：我要查清真相。\n赵明：你没有资格。\n" + ("冲突升级，秘密尚未公开。\n" * 4200)
    assert len(body) > 50_000
    source.write_text(body, encoding="utf-8")
    service = DramaService(_settings(tmp_path), runtime_values={"embedding_enabled": False})

    imported = service.import_script(str(source), title="五万字测试剧")
    assert imported["drama"]["chunk_count"] > 20
    assert service.get_drama(imported["drama"]["drama_id"])["title"] == "五万字测试剧"


def test_subtitle_import_removes_timing_but_keeps_dialogue(tmp_path: Path) -> None:
    source = tmp_path / "episode.srt"
    source.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n林晚：你认错人了。\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n董事长：欢迎大小姐。\n",
        encoding="utf-8",
    )
    loaded = load_script(source)
    assert "00:00" not in loaded.text
    assert "欢迎大小姐" in loaded.text
    assert len(loaded.source_units) == 2


def test_scanned_pdf_is_not_reported_as_success(tmp_path: Path) -> None:
    pypdf = pytest.importorskip("pypdf")
    source = tmp_path / "scan.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with source.open("wb") as handle:
        writer.write(handle)
    with pytest.raises(ScannedPdfRequiresOcr):
        load_script(source)


def test_authenticated_drama_routes(tmp_path: Path) -> None:
    fastapi = pytest.importorskip("fastapi")
    testclient = pytest.importorskip("fastapi.testclient")
    source = tmp_path / "api-script.txt"
    source.write_text(_sample_script(), encoding="utf-8")
    settings = _settings(tmp_path)

    class Control:
        memory_gateway = None

        @staticmethod
        def get_settings():
            return {"values": {"embedding_enabled": False}}

    app = fastapi.FastAPI()
    register_drama_routes(app, settings, Control(), token="secret")
    client = testclient.TestClient(app)
    assert client.get("/api/drama/status").status_code == 401

    headers = {"X-LingJi-Token": "secret"}
    response = client.post("/api/drama/import", headers=headers, json={"source_path": str(source)})
    assert response.status_code == 200
    drama_id = response.json()["drama"]["drama_id"]
    search = client.post(
        "/api/drama/search",
        headers=headers,
        json={"query": "继承人", "drama_id": drama_id, "limit": 5},
    )
    assert search.status_code == 200
    assert search.json()["results"]

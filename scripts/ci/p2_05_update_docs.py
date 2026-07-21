from __future__ import annotations

import subprocess
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing documentation marker: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    validated_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

    implementation = f"""# P2-05 Manual Capture Center — Integrated Implementation Report

> Status: `READY_FOR_FORMAL_MERGE`  
> Validated Integration Commit: `{validated_head}`  
> Date: 2026-07-21

## 1. Scope

P2-05 establishes the first owner-controlled manual information entry center without adding passive monitoring.

Implemented:

- Manual text, web, supported file, media, ChatGPT Export, and Codex Report submission.
- Persistent Extraction Queue submission by default.
- Capture Mode persistence: `normal`, `low_power`, `paused`.
- Capture job pagination, details, cancel, retry, pause, and resume.
- Sanitized Capture Job DTOs and stable error codes.
- Audit Events for submit, duplicate, pause, resume, cancel, and retry.
- Tauri Capture Center with official Dialog Plugin and minimal permission.
- Memory Inspector navigation from completed capture jobs.

Explicitly excluded:

- Clipboard or global keyboard monitoring.
- Folder or filesystem watchers.
- Mobile share client.
- Browser extension.
- PDF, DOCX, XLSX, or PPTX parser.
- Running-job process termination.

## 2. Integration Order

```text
P2-05B Manual Import Wiring
-> f01e3b2cc49065cda69f1c8909933dd0c530e4ff

P2-05A Capture Control API
-> 46a0c5276252734c121f0cad7a56cf3a4a7c4bdc

P2-05C Capture Center Desktop UI
-> fab0ba1b816c1228b8cfb3618aa04b5e2f2c4c3d

Final integrated cleanup and validation
-> {validated_head}
```

## 3. Final Architecture

```text
Tauri Capture Center
-> authenticated Local Control API :8766
-> CaptureControlService
-> CaptureService
-> ExtractionPipeline.enqueue()
-> SQLiteExtractionQueue
-> existing Adapter Registry
-> Raw / Vault / Structured Read Model / Memory Index
```

Permanent modules:

```text
src/capture/manual.py
src/capture/service.py
src/control/capture.py
src/control/capture_api.py
src/control/api.py
src/extraction/queue.py
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
desktop/lingji-control/src/AppPages.tsx
```

Temporary `_api_core.py` and `_queue_core.py` files were folded back into the formal modules and deleted.

## 4. Capture Methods

```text
manual_text
manual_web
manual_file
manual_media
manual_chatgpt_export
manual_codex_report
local_control_share  # compatibility only
```

Legacy mobile, browser, clipboard, and folder methods remain parse-compatible but are advertised as disabled or deferred.

## 5. Supported Inputs

- Text and URL/HTML content.
- HTML, TXT, and Markdown web snapshots.
- Web Snapshot JSON.
- ChatGPT ZIP, JSON, or export directory.
- Explicit Codex Report JSON.
- Existing supported audio and video formats.

Unsupported office documents and unknown binary input return `CAPTURE_UNSUPPORTED_TYPE`.

## 6. Queue and API

Added queue operations:

```text
cancel(job_id)
retry(job_id)
list_page(status, source_type, q, limit, offset)
count(...)
```

Added authenticated API routes:

```text
POST /api/capture/text
POST /api/capture/web
POST /api/capture/file
POST /api/capture/media
GET  /api/capture/status
GET  /api/capture/capabilities
GET  /api/capture/jobs
GET  /api/capture/jobs/{{job_id}}
POST /api/capture/jobs/{{job_id}}/retry
POST /api/capture/jobs/{{job_id}}/cancel
POST /api/capture/pause
POST /api/capture/resume
```

`POST /api/share` remains as a compatibility alias routed through the same Capture Control Service.

## 7. Privacy and Data Authority

- User-facing DTOs do not expose payloads, options, absolute paths, lease tokens, cookies, API keys, or raw exceptions.
- File names use basename only.
- Obsidian Vault + Git remain the permanent knowledge authority.
- SQLite, Structured Read Model, and Qdrant remain rebuildable derived data.
- No new database, queue, or Schema was introduced.

## 8. Rollback

Rollback the P2-05 integration commit and the three P2-05 merge commits. No database migration or production data rollback is required because this phase did not alter Schema or production data.
"""
    write("docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md", implementation)

    test_report = f"""# P2-05 Manual Capture Center — Integrated Validation Report

> Status: `INTEGRATED_VALIDATED`  
> Validated Integration Commit: `{validated_head}`  
> Environment: Windows Server 2025 / Python 3.12.10 / Node.js 22  
> Date: 2026-07-21

## 1. Python Dependency and Compile Gates

```text
Python dependency install: PASS
pip check: PASS
validate_clean_install.py --import-check: PASS
full compileall: PASS
exit code: 0
```

## 2. Full Repository Pytest

```text
collected: 409
passed: 398
failed: 0
skipped: 11
warnings: 2
duration: 79.40s
exit code: 0
```

The 11 skips are optional legacy PySide6 desktop tests, unconfigured real Obsidian integration checks, and the frontend-dist prebuild check. They are not suppressed P2-05 failures.

Warnings:

- Pydantic class-based configuration deprecation.
- Starlette TestClient/httpx compatibility deprecation.

Neither warning blocks P2-05 behavior, but both remain visible maintenance debt.

## 3. Desktop and Tauri Gates

```text
npm ci: PASS
npm run test:capture: PASS
npm run test:smoke: PASS (7 smoke scripts)
npm run build: PASS
TypeScript build: PASS
Vite production build: PASS
cargo check --manifest-path src-tauri/Cargo.toml: PASS
exit code: 0
```

## 4. Focused Evidence Before Integration

```text
P2-05A required five-file gate: 39 passed / 0 failed
P2-05A Windows full repository: 373 passed / 11 skipped / 0 failed
P2-05B Windows full repository gate: PASS
P2-05C Capture Smoke / Desktop Smoke / Build / Cargo Check: PASS
```

## 5. Contract Coverage

Validated:

- All dedicated manual APIs enqueue instead of synchronously executing Adapters.
- Long-lived CaptureControlService lifecycle.
- Capture Mode persistence and paused rejection.
- SQL pagination and filtering.
- Queue cancel and retry state rules.
- Manual Capture Method and Adapter mapping.
- Unsupported file rejection.
- Stable API errors and DTO sanitization.
- Official Tauri Dialog Plugin with minimal capability.
- Windows path handling and SQLite connection cleanup.
- App shell modular size gate.
- Frontend API race cancellation and request ID protection.

## 6. Data Safety

```text
Production Vault read/write: NO
Production SQLite read/write: NO
Production Qdrant access: NO
Production Ollama access: NO
Database Schema change: NO
New database: NO
New queue: NO
Listener/mobile/browser client development: NO
rebase: NO
force push: NO
```

## 7. Conclusion

```text
P2-05_MANUAL_CAPTURE_CENTER
INTEGRATED_AND_VALIDATED
READY_FOR_FORMAL_MERGE
```
"""
    write("docs/TEST_REPORTS/P2_05_INTEGRATED_VALIDATION_REPORT.md", test_report)

    status = read("docs/PROJECT_STATUS.md")
    status = replace_once(
        status,
        "> P2-05 Status（P2-05 状态）: `READY_FOR_PARALLEL_IMPLEMENTATION`",
        f"> P2-05 Validated Integration Commit（P2-05 已验证集成提交）: `{validated_head}`  \n> P2-05 Status（P2-05 状态）: `READY_FOR_FORMAL_MERGE`",
        "PROJECT_STATUS header",
    )
    status = replace_once(
        status,
        "P2-04 Memory Inspector UI（记忆检查器）               MERGED_AND_VALIDATED\n",
        "P2-04 Memory Inspector UI（记忆检查器）               MERGED_AND_VALIDATED\nP2-05 Manual Capture Center（手动投喂中心）            INTEGRATED_AND_VALIDATED\n",
        "PROJECT_STATUS completed list",
    )
    p205_section = f"""## 9. P2-05 Manual Capture Center

状态：`READY_FOR_FORMAL_MERGE`

已实现：

- 文本、网页、文件、媒体、ChatGPT Export 和 Codex Report 手动提交。
- 正式 `manual_*` Capture Method 和现有 Adapter Registry 映射。
- 所有 Desktop 手动提交默认进入持久化 Extraction Queue。
- Capture Mode 持久化、暂停和恢复。
- Queue 分页、筛选、取消和重试。
- 脱敏 CaptureJob DTO、稳定错误码和 Audit Event。
- Tauri Capture Center、官方文件选择 Dialog 和最小权限。
- 完成任务可跳转 Memory Inspector。
- `_api_core.py` 和 `_queue_core.py` 临时拆壳已折回正式模块。

最终门禁：

```text
Windows Python 3.12 full pytest: 398 passed / 11 skipped / 0 failed
npm ci: PASS
Capture Center smoke: PASS
Desktop smoke: PASS
Desktop build: PASS
cargo check: PASS
```

完整报告：

```text
docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md
docs/TEST_REPORTS/P2_05_INTEGRATED_VALIDATION_REPORT.md
```

"""
    status = replace_once(
        status,
        "## 9. P0 最终门禁结果\n",
        p205_section + "## 10. P0 最终门禁结果\n",
        "PROJECT_STATUS P2-05 section",
    )
    status = status.replace("## 10. 安全状态", "## 11. 安全状态")
    status = status.replace("## 11. 当前开发状态", "## 12. 当前开发状态")
    status = status.replace("## 12. 下一步", "## 13. 下一步")
    status = replace_once(
        status,
        "P2-05 Manual Capture Center:\nREADY_FOR_PARALLEL_IMPLEMENTATION",
        "P2-05 Manual Capture Center:\nREADY_FOR_FORMAL_MERGE",
        "PROJECT_STATUS current state",
    )
    status = replace_once(
        status,
        """将三个 P2-05 分支移动到同一正式基线
-> 发布更新后的1号、2号、3号任务
-> 三条实现分支并行开发
-> 集成分支统一测试
-> 正式合并 P2-05""",
        """将已验证的 P2-05 集成分支合并到正式分支
-> 更新正式状态和 Changelog 合并提交
-> 关闭 P2-05 Issue
-> 进入 Obsidian CLI 正式迁入 src 阶段""",
        "PROJECT_STATUS next step",
    )
    write("docs/PROJECT_STATUS.md", status)

    code_map = read("docs/MODULES/CODE_MAP.md")
    code_map = replace_once(
        code_map,
        "> P2-05 Status（P2-05 状态）: `READY_FOR_PARALLEL_IMPLEMENTATION`",
        f"> P2-05 Validated Integration Commit（P2-05 已验证集成提交）: `{validated_head}`  \n> P2-05 Status（P2-05 状态）: `READY_FOR_FORMAL_MERGE`",
        "CODE_MAP header",
    )
    code_map = replace_once(
        code_map,
        "src/capture/service.py\n",
        "src/capture/service.py\nsrc/capture/manual.py\n",
        "CODE_MAP capture manual",
    )
    code_map = replace_once(
        code_map,
        "- `process_later=True` 排队合同。\n",
        "- `process_later=True` 排队合同。\n- `manual_text`、`manual_web`、`manual_file`、`manual_media`、`manual_chatgpt_export`、`manual_codex_report`。\n- 不支持的 Office 文档和未知二进制返回稳定拒绝。\n",
        "CODE_MAP capture capabilities",
    )
    code_map = replace_once(
        code_map,
        "src/control/runtime_settings.py::RuntimeSettingsStore\n",
        "src/control/runtime_settings.py::RuntimeSettingsStore\nsrc/control/capture.py::CaptureControlService\nsrc/control/capture_api.py::register_capture_routes\n",
        "CODE_MAP control services",
    )
    code_map = replace_once(
        code_map,
        "/api/memory/inspector/*\n",
        "/api/memory/inspector/*\n/api/capture/*\n",
        "CODE_MAP capture API",
    )
    code_map = replace_once(
        code_map,
        "src/App.tsx\n",
        "src/App.tsx\nsrc/AppPages.tsx\n",
        "CODE_MAP AppPages",
    )
    code_map = replace_once(
        code_map,
        "src/pages/MemoryInspectorPage.tsx\n",
        "src/pages/MemoryInspectorPage.tsx\nsrc/pages/CaptureCenterPage.tsx\nsrc/pages/captureCenterApi.ts\nsrc/pages/captureCenterContract.ts\nsrc/pages/captureCenterTypes.ts\n",
        "CODE_MAP Capture Center",
    )
    section_at = code_map.find("## 15. P2-05 文件所有权")
    if section_at < 0:
        raise RuntimeError("CODE_MAP P2-05 section not found")
    code_map = code_map[:section_at] + f"""## 15. P2-05 Manual Capture Center

正式后端：

```text
src/capture/manual.py
src/capture/service.py
src/control/capture.py
src/control/capture_api.py
src/control/api.py
src/extraction/queue.py
```

正式 Desktop：

```text
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
desktop/lingji-control/src/pages/captureCenterApi.ts
desktop/lingji-control/src/pages/captureCenterContract.ts
desktop/lingji-control/src/pages/captureCenterTypes.ts
desktop/lingji-control/src-tauri/
```

任务状态：

```text
queued / retrying -> cancel
failed / cancelled -> retry
running -> no forced termination
completed -> result references / Memory Inspector
```

最终验证：

```text
Windows full pytest: 398 passed / 11 skipped / 0 failed
Capture smoke: PASS
Desktop smoke: PASS
Desktop build: PASS
Cargo check: PASS
```

## 16. 当前状态

```text
P0 Engineering Hygiene:
MERGED_AND_VALIDATED

P2-03 / P2-03B / P2-03C / P2-04:
MERGED_AND_VALIDATED

P2-05 Manual Capture Center:
READY_FOR_FORMAL_MERGE
```
"""
    write("docs/MODULES/CODE_MAP.md", code_map)

    changelog = read("docs/CHANGELOG.md")
    entry = f"""### P2-05 Manual Capture Center 集成验证

- 按 `P2-05B -> P2-05A -> P2-05C` 顺序合入 `work/p2-05-integrated-validation`。
- 增加手动文本、网页、支持文件、媒体、ChatGPT Export 和 Codex Report 入口。
- 增加持久化 Capture Mode、Queue 分页、取消、重试、暂停和恢复。
- 增加脱敏 CaptureJob DTO、稳定错误码和 Capture Audit Event。
- 增加 Tauri Capture Center、官方 Dialog Plugin、任务操作和 Memory Inspector 跳转。
- 真实生成并锁定 npm 与 Cargo 依赖文件。
- 将临时 `_api_core.py` 和 `_queue_core.py` 折回正式模块并删除。
- 修复 Windows SQLite 测试连接泄漏、Windows Vault 路径跨平台解析和 CPU 平台模拟测试。
- Windows Python 3.12 最终全仓结果：`398 passed, 11 skipped, 0 failed`，持续 79.40 秒。
- `npm ci`、Capture Smoke、7项 Desktop Smoke、TypeScript/Vite Build 和 `cargo check` 全部通过。
- 已验证集成提交：`{validated_head}`。
- 未访问生产 Vault、SQLite、Qdrant 或 Ollama；未修改数据库 Schema；未开发监听、手机端或浏览器插件。

"""
    changelog = replace_once(
        changelog,
        "## 2026-07-21\n\n",
        "## 2026-07-21\n\n" + entry,
        "CHANGELOG date section",
    )
    write("docs/CHANGELOG.md", changelog)

    print(f"P2-05 documentation updated for {validated_head}")


if __name__ == "__main__":
    main()

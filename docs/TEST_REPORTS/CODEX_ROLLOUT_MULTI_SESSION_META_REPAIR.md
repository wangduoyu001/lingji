# Codex Rollout 多 session_meta 修复 + 全盘运行优化（2026-09-19 晚）

验证提交：本轮修复提交（基于 6ec7468a）。
机器：本机 macOS（darwin 25.5.0 arm64），Python 3 + pytest 8.4.2。
范围：`src/extraction/adapters/codex.py`、`src/extraction/registry.py`、`tests/test_owner_codex_rollout_adapter.py`；另含对运行中生产实例（127.0.0.1:8766，data-root=production）的只读诊断与两项运维动作（备份、向量补齐、Obsidian 通道恢复）。

## 背景（四路并行只读调查结论）

1. **扫描失败根因**：生产每轮 partial_failure 19 的直接根因是 `CodexRolloutAdapter.detect_schema` 拒绝"同一 rollout 文件含多条不同线程 session_meta"（Codex compact/fork 合法形态）。17 个文件属此形态（源自 2026-08-26 同一原始会话的连续压缩分支），2 个文件无可提取消息。真实拒绝原因被 `registry._detection_reason` 的兜底文案掩盖。19 个 job 已是终态（max_attempts=1），幂等键命中旧失败记录，永不重试。
2. **向量缺口**：3132 个 chunk 缺口全部来自当日新采集的 automatic memory snapshot；入库路径只写词法索引，15 分钟调度器的自动回填只覆盖消息层集合，不覆盖 chunk 集合，缺口不会自动补齐。
3. **运行体检**：23 个 GET 端点全部可达。严重问题：零备份、chat 模型主备双缺失（qwen3:8b 未安装）、`/api/settings` 明文回显 zhipu_api_key、Obsidian CLI 超时导致 Vault 写入断路（health 漏报）。
4. **仓库核查**：6ec7468a 验收文档已同步（CHANGE_ACCEPTANCE_LOG/PROJECT_STATUS/LOCAL_EXECUTION/测试报告均在同一提交内）；`check_acceptance_sync.py` PASS；主仓库根目录停在旧验收分支且有 12 个未提交修改（独立并行工作，本轮未触碰）。

## 代码修复内容

- `detect_schema`：移除"多 session_meta 身份即拒绝"；首条 session_meta 线程 id（与文件名一致）为文件身份，后续 id 视为 compact/fork 延续。
- `extract`：改为首条身份 + `extra_identities` 记录 warning（不再抛错）；无身份或无消息仍拒绝。
- `registry._detection_reason`：对所有带 `detect_schema` 的适配器透出真实原因，取代兜底文案。
- 测试：`test_rollout_requires_payload_session_identity`（无身份仍拒绝）+ `test_rollout_accepts_compaction_appended_session_meta_using_first_identity`（接受延续、首条身份、warning、external_id 正确）。

## 测试命令与结果

```bash
python3 -m pytest tests/test_owner_codex_rollout_adapter.py -q          # 15 passed
python3 -m pytest tests/test_automatic_memory_adapters.py tests/test_chatgpt_importer.py tests/test_observability_api.py tests/test_task6p_queue_persistence_redaction.py -q   # 69 passed
python3 -m pytest tests/ -k "rollout or extraction or automatic_memory" -q   # 496 passed, 6 failed, 1 skipped
```

6 个失败经 `git stash` A/B 对比确认为 HEAD（6ec7468a）既有失败，与本轮改动无关：
- `tests/evaluation/test_automatic_memory_end_to_end.py` 5 项（质量门/升格存储断言）
- `tests/test_automatic_memory_context_pack.py::test_hybrid_diagnostics_are_per_call_and_semantic_failure_is_safe`（语义失败诊断期望 `semantic_query_failed`、实际 `no_matches`）

## 运行实例优化（对 production 实例的实际操作）

1. **首次完整备份**：`POST /api/backups` profile=full include_raw=true → LJ-BACKUP-20260919-200242-30c483d6.zip，559 文件 / 2.39GB，SHA256 校验 559/559 通过。消除"零备份"。
2. **向量补齐**：`POST /api/observability/vectorize` 循环 17 轮（每轮 200 条，约 27 秒/轮，共约 8 分钟）→ coverage 83.8% → **100%**（19329/19329，missing=0）。
3. **Obsidian 通道恢复**：根因=CLI 在 `/Applications/Obsidian.app/Contents/MacOS/obsidian-cli`（官方自带，不在 PATH）且 Obsidian 应用未运行。已 `PATCH /api/settings` 显式配置 `obsidian_cli_path` 并启动 Obsidian 应用 → `/api/obsidian/status` state=healthy、issues=[]。
4. **sidecar 重打包装机（22:05–22:10）**：`scripts/build_macos_sidecar.sh`（本机 python3 + PyInstaller 6.21.0，onedir 182 文件）构建含本修复的新二进制（SHA-256 `6e55bf1c…`，contract check 通过），替换 `/Applications/灵机.app/Contents/Resources/` 三件套（lingji-core.exe + lingji_core_lib + manifest），旧版备份至 `app-data/rollback-sidecar-20260919/`。
   - **装机坑（未来每次 mac 装机必做）**：PyInstaller 产物直接装入 App 后，完整服务模式启动即崩（DiagnosticReports 报 `CODESIGNING / Invalid Page / SIGKILL`；`--check-config` 最小模式不触发）。修复=对 `lingji_core_lib` 全部 80 个 `.so`/`.dylib` 及主 exe 逐个 `codesign --force --sign -` 重签 ad-hoc。重签后手动完整启动与 App 拉起均正常。
   - 装机后验收：health degraded（仅剩 ffprobe 一条已知 warning）、`search_memory("薏仁")` 正常返回、memory healthy（core 1）、vector healthy（19329/19329）、新 sidecar PID 41360 监听 8766。构建中间产物（build/ 与 tauri binaries，共约 202MB）已清理。
   - 19 个终态失败 job 未重置（等 Codex 侧清理后由下一轮扫描验证修复效果）。

## 未执行 / 待主人决策

- 适配器修复未部署到生产、19 个终态 job 未重置（需写生产数据库，待确认）。
- 2 个"无可提取消息"文件仍将失败（错误文案已可透出真实原因）；是否改为 skip 语义未决。
- chat 模型主备双缺失（qwen3:8b 未安装）：改分配为已装模型（如 qwen2.5:7b-instruct）或 `ollama pull qwen3:8b`，待选。
- `/api/settings` 明文回显 API key：需代码修复（GET 脱敏）。
- `distill_provider` 覆盖为 zhipu（云端）偏离 local 默认：隐私决策待确认。
- 6 个既有测试失败（语义诊断分类 + evaluation 质量门）需独立修复。
- 567 张待复核卡堆积（auto_review=OFF）、capture 20 个 failed 滞留、两个 chatgpt_export 源指向 acceptance 目录、主仓库脏工作区处置。

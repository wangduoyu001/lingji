# TEST REPORT — 自动记忆晋升管线（AUTO_MEMORY_PROMOTION_PIPELINE）

- 日期：2026-09-22（代码 + 真机验收同日完成）
- 分支/HEAD：`codex/owner-source-intake-mac-repair`，实现 `9a614cf1` + 修复 `4d6b42b0`/`f2a82fa0`/`52033dd9` + 文档提交
- 执行环境：macOS（darwin 25.5.0 arm64）；生产数据根 `~/LingJiAcceptance/osimr-7e7f0707/app-data/production`
- 最终装机：`/Applications/灵机.app` sidecar SHA-256 `6435ef10…`（182 运行时文件 + 80 个 .so/.dylib 逐个 ad-hoc 重签，`codesign --verify --deep --strict` 通过）
- 结论：**本机验收通过，待主人最终确认**。App 保持打开。

## 自动测试

| 套件 | 结果 |
| --- | --- |
| `tests/test_auto_promotion_pipeline.py`（14 例，含 limit 空转回归） | 14 passed |
| `tests/test_automatic_memory_distillation.py`（17 例，含 3 例饿死回归） | 17 passed |
| `tests/test_memory_lifecycle.py` + `tests/test_automatic_memory_runtime.py` | 通过 |
| `tests/test_observability_api.py` + settings 四件套 | 26 passed |
| `tests/test_auto_review_*` + `tests/test_auto_memory_promotion.py` + gateway | 71 passed |
| `tests/test_packaged_control_api.py` | 18 passed |

合计 166 passed, 0 failed。门禁 `scripts/check_acceptance_sync.py` PASS。

## 真机验收记录（production）

1. **装机**：三轮"构建→覆盖安装→codesign 全量重签→health 验证"迭代（0799ebcd → 9c542d53 → 6435ef10）。每轮 health 均为 degraded 且仅剩已知 ffprobe warning（与装机前基线一致）；`confidence` 列由 distill 首轮自动 ALTER 迁移成功。
2. **开关**：`PATCH /api/settings` 开启 `auto_promote_enabled`，runtime_settings.json 落盘确认；运行中切换 ≤15s 生效。
3. **Evolving 轨**：首轮 5 条旧行（confidence 为空）转 Evolving，原因码 `confidence_missing`；后续 `title_conflict`、`category_not_whitelisted + notification_like + confidence_below_threshold` 等分支真实触发。共 19 个带日期时间线文件，frontmatter（topic/status/confidence/updated/tags）齐全，幂等 marker 就位。
4. **晋升正路**：distill 修复后新行携带模型自评 confidence（首批 8 条：1.0×1、0.9×4、0.8×4）。真实晋升 1 条进 `03-Knowledge/Core-Memory/General/`：frontmatter `memory_tier: core`、`confidence: 0.9`、`proposed_by: lingji-auto`、来源追溯（conversation_id@revision + 模型名）齐全。
5. **审计**：`auto_promotion_decision` 事件 25 条（24 evolving + 1 promoted），`verify_auto_promotion_chain` 校验 True；篡改检测由单测覆盖。
6. **回滚**：关开关后 `run_once` 返回 `status: disabled`，审计事件 25→25 零写入；随后恢复开启（保持主人要的最终态）。
7. **附带修复的实证**：distill 修复前 finished 全部 0.0s 空转、ready 停在 54；修复后单条 9.5-11.5s 真实云端提炼，ready 54→61 并持续增长（549 个从未提炼的会话开始被消化）。

## 验收中发现并修复的回归

| 提交 | 问题 | 修复 |
| --- | --- | --- |
| `4d6b42b0` | 历史 ready 行 message_count 旧口径与实际不符 → 每轮满足候选条件却被秒跳且永不修正 | 秒跳路径无模型调用修正口径 |
| `f2a82fa0` | 秒跳判断 SELECT 漏取 status 列，取不到默认按 ready → superseded 终态行每轮空转占位，**549 个会话从未被提炼**（生产真根因） | 候选查询排除 superseded；真实读取 status 列 |
| `52033dd9` | 晋升管线 limit 截断在已决过滤之前 → 最老已决行占满每轮名额，首轮后 processed 恒 0 | 先过滤已决再截断 limit |

## 限制与已知事项

1. **存量消化规模**：54 条旧行 + 后续新行中未达标者将持续进 Evolving（当前 19 个文件，随管线轮转渐进增长）。这是"未达标不静默丢弃"的设计行为；主人可审阅后删除或整理，git 可回溯。
2. **门槛是确定性规则**：晋升质量取决于提炼模型自评置信度。首批已出现任务性内容（如"验收文档同步任务分配"）达标晋升——若觉得过宽，可在设置页调高"晋升置信度门槛"（如 0.95）或调低"每日自动晋升上限"。
3. 未重跑 2026-09-19 报告的 229 项全量回归；语义去重依赖 bge-m3（生产实测 1 条晋升经过真实嵌入比对）。
4. 旧格式行（confidence 空）按设计永不自动晋升；只有新提炼行参与门槛。

## 回滚

关闭 `auto_promote_enabled`（Desktop 设置页"记忆自动化"组或 `PATCH /api/settings`）。已晋升文件属既有 Core，不做批量删除。应用级回滚：`app-data/rollback-sidecar-20260922-auto-promote/`（上一版 sidecar 三件套，SHA `0b066312…`）。

## 追加（深夜二轮）：主人实测反馈的两个显示问题

主人反馈"永久记忆还是 1、向量未开启"。诊断与修复（提交 `97ece3d8`/`edd7ac8b`/`d9d505fe`）：

1. **永久记忆计数不动**：UI 计数来自 `memory_documents` 投影（`core_memories`），而 `sync_core`
   只在 gateway 启动时跑一次，运行中晋升的 Core 文件要等重启才进投影。修复：晋升管线新增
   `post_promotion_sync` 回调，每轮有晋升后自动调 `IncrementalMemorySynchronizer.sync_core`
   （MemoryDatabase 每次调用独立连接，无句柄残留）。实测：计数 1 → 11（含后续真实晋升）。
2. **向量显示未开启**：两层原因。其一，`/api/overview` 的嵌入状态直接读懒加载 provider 的
   历史计数（`available = 有成功且无 last_error`），启动早期一次失败即恒 false；现改为
   status 路径真实探活（`reset_failures` + 一次轻量 embed，失败缓存 60s）。其二，探活如实
   暴露了 **Ollama 服务本身已退出**（Connection refused ×8）——显示是诚实的。Ollama 已用
   其既有 launchd 服务（`com.ollama.serve.plist`）重新托管，开机自启。
3. 修复后实测：`core_memories=11`、`embedding available=true (bge-m3, 1024 维, healthy)`、
   `vector state=healthy (19,801 向量，含 54 个新晋升 chunk 的补齐)`。
4. 附加单测：`tests/test_vector_status_probe_fallback.py`（3 例）、
   `tests/test_embedding_status_probe.py`（5 例）；相关套件合计 83 passed。
5. 已知既有缺陷（未修，记录待办）：sidecar 停机时 `ExtractionWorker remained alive after
   stop` 导致 shutdown RuntimeError（每次退出日志可见，不影响运行中服务）。
6. 运维提醒：Ollama 现由 launchd 管理；`auto_promote_poll_seconds` 仅 config 层（运行中不可调）。

## 追加（深夜三轮）："永久记忆还是 0" 的真正根因

主人 UI 一直显示 0 而后端实测 11：首页"已入永久记忆"轮询
`/api/memory/inspector/cards-summary`，该接口每请求全量测量 590 张卡，生产库上耗时
18-19s，而首页每 20s 轮询一次——任何重叠/抖动即超时，前端 `cards ?? 0` 把无数据显示成 0。
修复（`c0ba6262`）：默认 viewer 的 summary 结果缓存 60s 并以单锁串行重算（显式 viewer 不缓存）。
实测：首次 18.8s 计算，后续命中 0.001-0.017s，permanent=11 稳定。新增 1 例缓存单测（34 例 projector 套件全过）。
装机 sidecar SHA `d13becc8…`。
另：连续三次观察到 App 在运行中被退出（sidecar 随之停机并报既有 ExtractionWorker 停机缺陷）——
若是主人手动退出测试，重开灵机即可，修复已在装机内生效。

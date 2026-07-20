# P2-01 Tauri Vector Center UI Test Report

Updated: 2026-07-20  
Status: `IMPLEMENTED_AWAITING_LOCAL_UI_VALIDATION`

## 1. 任务目标

在唯一正式桌面 UI `desktop/lingji-control/` 中增加只读“向量中心”，通过 Local Control API 展示 Memory Index、Embedding、Qdrant、向量覆盖率、状态来源、快照时效、错误和 Runtime warnings。

本任务不提供模型切换、Collection 创建、重建、删除或任何生产数据写操作。

## 2. 开始基线

```text
Repository: wangduoyu001/lingji
Formal branch: feature/second-brain-memory
Baseline: 9ab3c55074b0e56dac9ac8adccba934627bedd90
```

开发前比较结果：正式分支与指定基线 identical，ahead 0，behind 0。

## 3. 开发分支

```text
work/p2-01-vector-center-ui
```

该分支从指定基线创建，仅在本分支提交；未 force push，未 rebase 或合并正式分支。

## 4. 修改文件

```text
desktop/lingji-control/package.json
desktop/lingji-control/scripts/ui-modular-smoke.mjs
desktop/lingji-control/scripts/vector-center-smoke.mjs
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/pages/BrainStatusPage.tsx
desktop/lingji-control/src/pages/VectorCenterPage.tsx
desktop/lingji-control/src/pages/VectorCenterPage.css
docs/TEST_REPORTS/P2_01_VECTOR_CENTER_UI_TEST_REPORT.md
```

未修改 `src/` 后端、P1-05 验收脚本、Python 测试、requirements 或 `second_brain/`。

## 5. 页面结构

向量中心包含：

1. 顶部刷新、自动刷新、状态时间、Workspace、三个接口来源和 stale 状态。
2. 文档、Chunk、向量、覆盖率核心指标。
3. 实际 Embedding 模型、实际维度、Qdrant 模式和 Collection 摘要。
4. Memory Index 详情。
5. Embedding 配置模型与实际模型详情。
6. Qdrant Ready、Collection、维度、距离和 rebuild-required 详情。
7. 覆盖率进度条、Expected、Indexed、Missing 和缺失 Chunk ID。
8. 接口错误、Runtime warnings 和状态来源说明。

`App.tsx` 仅负责页面装配，没有接口请求和业务转换逻辑。远程文件内容为 62 行，专属 smoke 按尾部换行计数为 63 行，均低于 100 行限制。

## 6. API 映射

正式数据源：

```text
GET /api/memory/status
  -> Memory Index、文档、Chunk、Core Memory、Revision、数据库与 integrity

GET /api/vector/status
  -> Embedding、Qdrant、Collection、向量、维度、Ready、rebuild-required

GET /api/vector/coverage
  -> Expected、Indexed、Missing、Coverage、缺失 Chunk ID

GET /api/brain/status
  -> 顶部摘要一致性与 Runtime warnings 补充
```

所有请求使用现有 `LingJiApi.get()`，由连接层指向 authenticated Local Control API 8766。页面没有 Qdrant、Ollama、SQLite、8765 或 8767 直连。

## 7. 状态颜色合同

```text
healthy / ready              -> success / 绿色

degraded / stale             -> warning / 黄色
configuration_required       -> warning / 灰黄
disabled                     -> neutral / 灰色
unavailable / failed         -> error / 红色
rebuild_required             -> warning/error 语义提示
未知后端字符串               -> 原样显示 + neutral
```

复用现有 `.pill`、`.pill.success`、`.pill.warning` 和 `.pill.error`，未引入组件库。

## 8. null 与假 0 处理

数量和比例统一使用显式 null 判断：

```text
null / undefined -> "-"
真实 0           -> "0"
coverage null    -> "-"
coverage 0       -> "0.00%"
```

同时修正 Brain Status 的向量摘要：

```typescript
vector_count ?? "-"
```

不再使用 `vector_count || 0` 把未知状态伪装为零。

## 9. stale 与 snapshot 处理

页面分别显示 Memory、Vector 和 Coverage 的 `source` 与 `as_of`。

说明合同：

```text
live        = 当前拥有 MemoryGateway 的进程实时生成
snapshot    = Local Control API 从 memory_status.json 读取
unavailable = 尚无可读取的运行状态
stale       = 快照超过有效时间，数据可能不是最新
```

stale 使用警告提示，不翻译为“系统损坏”。刷新时保留已有数据。

## 10. 错误降级策略

四个请求通过一个 `Promise.allSettled()` 独立处理：

- `memoryError`
- `vectorError`
- `coverageError`
- `brainError`

行为：

1. 三个正式接口首次全部失败时显示主要连接/令牌错误。
2. 部分失败时继续显示成功面板。
3. 刷新失败时保留上次成功数据并标注本次失败。
4. 401 的 FastAPI `detail` 由现有 API 客户端原样转换为错误信息。
5. 服务断开时保留上次数据，不生成本地假状态。
6. 不进行无限重试。

## 11. 自动刷新策略

- 页面首次进入自动加载。
- 手动刷新按钮。
- 默认每 15 秒自动刷新。
- `inFlight` 引用避免重复并发请求。
- 浏览器标签不可见时定时器不发请求。
- 标签重新可见时立即刷新。
- 页面切走导致组件卸载，interval 与 visibility listener 同步清理。
- 刷新期间不清空旧数据。

## 12. Smoke 测试

新增：

```text
desktop/lingji-control/scripts/vector-center-smoke.mjs
```

检查：页面、导航、PageId、App 装配、三个正式接口、Coverage、rebuild-required、`Promise.allSettled()`、无 POST/PATCH、无直连 URL、无 8765/8767、App 行数限制。

已在隔离重建的前端文件集运行：

```text
node scripts/vector-center-smoke.mjs
```

结果：

```text
Vector Center smoke passed; App.tsx=63 lines
```

补充执行隔离严格 TypeScript 检查，覆盖 `VectorCenterPage.tsx` 和共享状态类型：通过。

`package.json` 的 `npm run test:smoke` 已加入 `vector-center-smoke.mjs`。`ui-modular-smoke.mjs` 已加入 VectorCenter 文件、导航、App 装配和接口检查。

## 13. Build 测试

计划命令：

```bash
cd desktop/lingji-control
npm ci
npm run test:smoke
npm run build
```

本执行环境没有完整 Git checkout、`node_modules` 和可用的依赖下载网络，因此未执行完整 npm smoke 与 Vite/Tauri 前端 build。

不得把隔离脚本通过解释为完整项目构建通过。

## 14. 未运行项目

```text
npm ci
npm run test:smoke（完整套件）
npm run build
npm run tauri dev
真实 8766 + Token 页面加载
真实 live/snapshot/stale 切换
真实部分接口故障 UI
1250px 与 Windows Tauri 窗口视觉验收
P1-05 Windows/Ollama/bge-m3/Qdrant 本机验收
```

以上均为 pending local validation。

## 15. 已知限制

1. 当前页面只读，不提供安全 Collection 重建。
2. 当前页面只读，不提供模型切换。
3. Runtime warnings 目前来自 `/api/brain/status`，三个详细状态接口自身不包含 warnings。
4. 快照时间取决于 Gateway 发布频率；空闲运行时可能显示 stale。
5. 本报告不证明 bge-m3 已成为生产默认模型。
6. 页面尚未在用户 Windows/Tauri 真机中完成视觉和交互验收。

## 16. 数据安全说明

本任务：

- 不修改 Vault。
- 不访问或修改 `lingji_memory.db`。
- 不访问或修改 Qdrant。
- 不调用 Ollama。
- 不修改生产配置。
- 不创建、删除或重建 Collection。
- 不添加 POST/PATCH 写操作。
- 不修改 P1-05 后端与验收脚本。
- 不包含 Token、数据库、日志或真实个人数据。

## 17. 回滚方式

在合并前可直接删除开发分支。

若未来合并后需要回滚，按顺序 revert：

```text
docs(ui): document p2-01 vector center
test(ui): add vector center smoke coverage
feat(ui): add vector center page
```

回滚只影响前端页面、前端 smoke 和本报告，不需要生产数据回滚。

## 18. 下一步建议

```text
等待 P1-05 本机验收反馈
验收通过后进行 UI 分支 rebase/合并
之后再开发安全 Collection 重建与模型切换流程
```

在 P1-05 真机验收前，不提前宣称 bge-m3 已成为正式生产模型。

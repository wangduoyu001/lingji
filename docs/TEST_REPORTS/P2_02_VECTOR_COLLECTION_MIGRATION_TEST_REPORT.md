# P2-02 Vector Collection Migration Test Report

> Updated（更新时间）: 2026-07-20  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Validated Code Commit（已验证代码提交）: `8a4860553edfbb698665c7dcb1f8bfaf3f556eba`  
> Original Development Branch（原开发分支）: `work/p2-02-vector-collection-migration`  
> Status（状态）: `MERGED_AND_VALIDATED`  
> Evidence（证据来源）: 本机 Codex 验收汇总、真实 `bge-m3` 隔离验收和正式分支代码

## 1. 任务目标

实现一个安全的 Vector Collection Migration（向量集合迁移）工具，用于在不改变当前生产模型和生产 Collection（向量集合）的前提下，创建并验证替代候选 Collection。

迁移工具必须证明：

- 候选 Collection 包含 `lingji_memory.db` 中全部 Canonical Chunk（标准文本分块）。
- 使用请求的 Embedding Model（向量嵌入模型）。
- 实际向量维度有效。
- 向量数量精确匹配 Chunk 数。
- Coverage（覆盖率）为 100%。
- 激活和回滚参数完整。

## 2. 开发与合并信息

```text
Repository: wangduoyu001/lingji
Original baseline: a076b4f42b530077e7cff7dd3745cf2250293bae
Validated formal commit: 8a4860553edfbb698665c7dcb1f8bfaf3f556eba
Merge state: merged into feature/second-brain-memory
```

P2-02 已完成本机隔离验证并进入正式分支。

未执行 Force Push（强制推送）。

## 3. 修改文件

```text
docs/TEST_REPORTS/P2_02_VECTOR_COLLECTION_MIGRATION_TEST_REPORT.md
scripts/prepare_vector_collection_migration.py
scripts/validate_p2_02_local.py
src/retrieval/__init__.py
src/retrieval/collection_migration.py
src/retrieval/index_coordinator.py
tests/test_vector_collection_migration.py
```

最终汇总：

```text
7 files
1329 insertions
```

## 4. 数据权威

迁移点只来自：

```text
Obsidian Vault + Git
  -> lingji_memory.db
  -> MemoryIndexCoordinator.semantic_points()
  -> target Qdrant Collection
```

Qdrant（向量数据库）不是永久记忆权威。

工具不会从旧 Collection 读取正文来构建新 Collection。

## 5. 安全边界

本任务实现：

```text
plan（计划）
  -> build candidate（构建候选集合）
  -> validate exact vector count（验证精确向量数量）
  -> validate 100% coverage（验证完整覆盖率）
  -> validate active model and dimension（验证实际模型与维度）
  -> write atomic manifest（写入原子迁移清单）
  -> produce activation and rollback settings（生成激活和回滚参数）
```

本任务不执行：

```text
修改当前 Runtime Settings（运行时设置）
删除源 Collection
自动删除失败候选 Collection
重启 MCP 或 Local Control
修改 Vault 或正式 SQLite
切换生产 Embedding Model
```

## 6. 核心实现

新增：

```text
src/retrieval/collection_migration.py
```

核心对象：

- `VectorCollectionMigrationService`
- `VectorCollectionMigrationPlan`
- `VectorCollectionMigrationResult`
- `VectorCollectionMigrationError`

安全检查包括：

1. 源和目标 Collection 名不同。
2. Collection 名符合安全字符范围。
3. 目标模型名称有效。
4. Canonical Index（标准索引）至少包含一个 Chunk。
5. 每个 Canonical Point（标准向量点）都被提交。
6. Provider（提供器）为每个 Point 返回一个 ID。
7. Coverage 精确等于 `1.0`。
8. Missing 精确等于 `0`。
9. 目标 Collection 存在且 Ready（就绪）。
10. Provider 不报告 `rebuild_required`。
11. 目标向量数精确等于 Chunk 数。
12. 实际维度大于零。
13. Embedding Provider 已验证可用。
14. 实际激活模型与目标模型一致。
15. Provider 状态指向正确 Collection 和 Workspace（工作区）。

任意检查失败：

- 生成失败 Manifest（迁移清单）。
- 不生成 Activation Settings（激活设置）。
- 保留 Rollback Settings（回滚设置）。

## 7. Production Preparation CLI（生产准备命令行工具）

新增：

```text
scripts/prepare_vector_collection_migration.py
```

Plan-only（仅计划）模式：

```powershell
python scripts/prepare_vector_collection_migration.py `
  --model bge-m3 `
  --collection lingji_memory_production_bge_m3_1024_v1
```

Plan-only 不创建 Collection。

真正执行 Embedded Qdrant（嵌入式向量数据库）候选构建时，必须同时使用：

```text
--execute
--confirm-exclusive-qdrant
```

P2 验收没有执行正式生产候选构建。

## 8. Isolated Real Acceptance（真实隔离验收）

新增：

```text
scripts/validate_p2_02_local.py
```

验收环境：

```text
temporary Acceptance Workspace（临时验收工作区）
temporary Vault（临时知识库）
temporary lingji_memory.db
real Ollama bge-m3
Qdrant in-memory candidate Collection
real VectorCollectionMigrationService
atomic temporary migration Manifest
```

执行命令：

```powershell
python scripts/validate_p2_02_local.py --model bge-m3
```

本机 Codex 最终汇总：

```text
8/8 focused unit tests passed
real bge-m3 isolated acceptance passed
candidate coverage = 100%
missing = 0
production data modified = false
```

实际 `bge-m3` 密集向量维度在 P1/P2 验收链路中验证为 1024。

## 9. Manifest（迁移清单）

默认位置：

```text
<workspace reports>/vector-migrations/
```

Manifest 包含：

- 源和目标 Collection
- 源和目标模型
- Expected 和 Upserted 数量
- Vector Status（向量状态）
- Embedding Status（向量模型状态）
- Coverage
- Activation Settings
- Rollback Settings
- Validation Status（验证状态）

Manifest 不包含：

- Chunk 正文
- Memory 正文
- 原始向量
- Token（令牌）

写入使用临时文件后 Atomic Replace（原子替换）。

## 10. 测试范围

`tests/test_vector_collection_migration.py` 覆盖：

- 禁止复用当前活动 Collection
- 拒绝空 Canonical Index
- 完整候选验证和 Manifest
- `bge-m3` 激活参数
- 旧模型和旧 Collection 回滚参数
- Manifest 不包含正文
- 拒绝部分覆盖
- 失败候选没有激活参数
- 拒绝额外向量
- 拒绝错误实际模型
- 拒绝不完整 Upsert（写入）返回
- 支持 Ollama `:latest` 标签比较
- 成功和失败 Audit Event（审计事件）

重点单元测试与真实隔离验收均已完成。

## 11. 当前生产状态

```text
Migration tool merged             YES
Real bge-m3 isolated validation    PASS
Production candidate built         NO
Production model switched          NO
Source collection deleted          NO
Production Vault modified          NO
Production SQLite modified         NO
```

## 12. 已知限制

1. Runtime Settings 尚未把模型和 Collection 切换实现为一个 Atomic Transaction（原子事务）。
2. CLI 需要人工确认 Embedded Qdrant 的独占访问，不能自动识别所有外部进程。
3. 失败候选 Collection 保留用于诊断，不自动删除。
4. Retrieval Quality A/B Test（检索质量对比测试）尚未执行。
5. Remote Qdrant Alias（远程 Qdrant 别名）未实现。
6. Vector Center 当前只读。

## 13. 后续生产迁移顺序

生产迁移必须独立立项：

```text
review plan-only output
-> stop competing embedded Qdrant owners
-> build new production candidate Collection
-> verify exact count and 100% coverage
-> run retrieval quality comparison
-> apply controlled activation transaction
-> restart Gateway/MCP/8766
-> retain previous Collection for rollback
```

## 14. 最终结论

```text
P2_02_MERGED_AND_VALIDATED
```

P2-02 已合并正式分支，无需重复运行同一套本机隔离验收，除非迁移服务、Embedding Provider、Qdrant Provider 或 Workspace 合同发生相关变化。

下一步：P2-03 Structured Read Model（结构化读取模型）。

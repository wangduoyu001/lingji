# LingJi v1.1 默认值与 UI 可见性强制规范

> 关联架构：`docs/LINGJI_PERSONAL_MEMORY_OS_ARCHITECTURE_V1_1_ADDENDUM.md`  
> 状态：`APPROVED_POLICY`  
> 适用范围：P1-P7 所有可配置默认值、阈值、模型、路径、保留期、采样频率、降级策略和安全策略

---

## 1. 核心规则

凡是代码、配置、数据库或架构中存在可由主人决策的默认值，都必须在桌面 UI 中提供可见的设置入口。

禁止：

- 只把默认值写在 `config.py`、环境变量、常量或数据库中；
- 只有开发者知道参数含义；
- UI 只显示当前值，不显示默认值；
- UI 允许修改但不解释影响；
- 修改后无法恢复默认；
- 高风险参数修改后立即执行破坏性操作；
- 使用技术名称代替主人可理解的说明；
- 为了界面简洁而隐藏重要运行策略。

不是所有内部实现常量都需要暴露。只暴露主人有合理理由学习、选择和调整的配置；协议常量、数据库内部版本、加密算法内部参数等不可随意修改的值只显示说明，不提供编辑。

---

## 2. 每项可配置默认值必须包含的 UI 信息

每个设置至少显示：

```text
设置名称
设置用途
当前有效值
系统默认值
推荐值
是否已被主人覆盖
允许范围或可选项
单位
为什么推荐这个值
什么情况下应该修改
修改后会影响什么
是否需要重启
是否触发后台任务
是否产生额外磁盘、时间、GPU、Token 或费用
风险等级
恢复默认按钮
相关帮助或术语解释
```

推荐字段契约：

```text
SettingDefinition
- key
- group
- label
- description
- type
- default
- recommended
- recommendation_reason
- when_to_change
- minimum
- maximum
- choices
- unit
- scope
- restart_required
- task_required
- risk_level
- cost_impact
- storage_impact
- performance_impact
- privacy_impact
- dependencies[]
- conflicts[]
- learn_more
- editable
```

`recommended` 可以等于 `default`，但两者语义必须分开：

- `default`：系统在没有主人覆盖时采用的值；
- `recommended`：根据当前硬件、规模和使用方式给出的建议值。

硬件检测完成后，推荐值允许动态变化，但默认值不能静默改变。

---

## 3. UI 交互规范

### 3.1 状态标签

每项设置显示以下状态之一：

```text
使用系统默认
使用推荐值
主人已修改
等待生效
需要重启
存在风险
当前不可用
```

### 3.2 操作

每项设置至少支持：

- 修改；
- 保存；
- 取消未保存修改；
- 恢复该项默认；
- 查看影响；
- 查看说明。

每个设置组支持：

- 保存本组；
- 恢复本组默认；
- 只显示已修改；
- 搜索设置；
- 导出脱敏设置摘要；
- 查看最近修改记录。

### 3.3 高风险设置

以下类型必须先显示影响预览，再要求人工确认：

- 全量向量重建；
- Embedding 正式索引切换；
- 删除模型；
- 删除旧向量索引；
- 修改隐私范围；
- 开启云端 Provider；
- 修改自定义 Provider Base URL；
- 自动禁用 Provider；
- 清理活动、安全或调用审计；
- 修改模型或 Qdrant 根目录；
- 修改旧索引保留期；
- 修改高频硬件遥测；
- 允许局域网或公网发送 API Key。

影响预览显示：

```text
旧值
新值
受影响模块
预计任务数量
预计时间或工作量
预计新增/释放空间
是否影响当前服务
回滚方法
确认文字
```

---

## 4. 默认值分类与 UI 入口

| 默认值类别 | UI 入口 | 示例 |
|---|---|---|
| 硬件和采样 | 系统与算力 | 前台 2 秒、后台 5 秒、空闲 30 秒 |
| 算力模式 | 系统与算力 | 自动选择、GPU 优先、仅 CPU |
| 本地模型 | AI 与模型 | 默认 Embedding、ASR、OCR、视觉、重排模型 |
| 模型兼容性 | AI 与模型 | RAM/显存安全余量、基准样本规模 |
| 模型目录 | AI 与模型 / 存储 | `E:\LingJiData\models` |
| 向量索引 | 语义记忆 | 批次大小、覆盖率阈值、失败重试、旧索引保留期 |
| Qdrant 升级阈值 | 语义记忆 / 高级设置 | 20 万 Point、4 GB 预警 |
| 混合检索 | 记忆检索 / 语义记忆 | RRF 权重、候选数、是否启用 Reranker |
| 活动事件 | 活动中心 / 设置 | 遥测 24h、事件 30d、摘要 180d |
| 云端 Provider | AI 与模型 / 密钥与安全 | 默认关闭、费用限额、轮换周期 |
| 隐私范围 | 隐私与安全 | public/private/highly_sensitive 向量策略 |
| 文件检索 | 本地文件 | 白名单目录、文件类型、大小限制 |
| 存储和备份 | 存储与备份 | 路径、空间阈值、备份保留期 |

---

## 5. 10 个 ADR 的 UI 映射

### ADR-1 Qdrant Local Mode 阈值

UI：`语义记忆 > 高级设置 > 存储与规模`

可调：

- Point 黄色预警，默认 200,000；
- Point 迁移评估，默认 500,000；
- 存储黄色预警，默认 4 GB；
- 存储迁移评估，默认 8 GB；
- P95 查询预警，默认 250 ms；
- P95 迁移评估，默认 500 ms。

### ADR-2 默认 Embedding 模型

UI：`AI 与模型 > Embedding`

显示：

- 系统默认；
- 当前正式模型；
- 当前候选模型；
- 维度；
- 覆盖率；
- 新旧 Query Set 对比；
- 切换状态。

选择新模型不能立即切换正式索引。

### ADR-3 Source Collection 隐私范围

UI：`隐私与安全 > 语义索引范围`

可调：

- public 是否索引；
- private 是否索引；
- highly_sensitive 是否索引；
- Agent 权限；
- 排除目录。

提高隐私内容索引范围必须显示风险并确认。

### ADR-4 旧索引保留

UI：`语义记忆 > 索引版本`

默认：30 天、至少 2 个版本、至少一次回滚演练。

### ADR-5 云端 Provider 默认关闭

UI：`AI 与模型 > 云端 Provider`

每个 Provider 单独启用，显示密钥状态、连接、模型、费用和审计。

### ADR-6 私网策略

UI：`AI 与模型 > 自定义兼容 API > 网络安全`

选项：

- 本机服务；
- 局域网白名单；
- 公网 HTTPS。

### ADR-7 活动保留期

UI：`活动中心 > 保留与清理`

默认：

- 原始遥测 24 小时；
- 详细事件 30 天；
- 任务摘要 180 天；
- 安全审计 365 天。

### ADR-8 硬件遥测频率

UI：`系统与算力 > 监控频率`

默认：

- 前台任务 2 秒；
- 后台任务 5 秒；
- 空闲 30 秒；
- 最小化 60 秒；
- nvidia-smi 回退不少于 10 秒。

### ADR-9 模型和 Qdrant 目录

UI：`存储与备份 > 数据目录`

修改目录必须执行：空间检查、权限检查、迁移预览、停止相关任务、校验复制、切换、保留旧目录回滚。

### ADR-10 并行开发策略

这是开发治理决策，不作为普通运行设置。UI 只在未来的开发控制页面显示当前阶段、并行分支和共享热点锁，不允许普通运行 UI 修改架构开发顺序。

---

## 6. 后端要求

所有可配置默认值必须通过统一定义注册，不允许页面手写另一份默认值。

权威流程：

```text
后端 Setting Registry
→ FastAPI /api/settings
→ 桌面 UI 动态渲染
→ RuntimeSettingsStore 保存主人覆盖
→ Service 解析有效值
```

禁止：

```text
后端默认 = 30
前端默认 = 14
文档默认 = 7
```

推荐 API 返回：

```json
{
  "key": "activity_event_retention_days",
  "value": 30,
  "default": 30,
  "recommended": 30,
  "overridden": false,
  "definition": {
    "label": "详细活动事件保留天数",
    "description": "保留任务进度、模型加载和普通错误事件。",
    "when_to_change": "磁盘空间紧张时可以降低；需要长期诊断时可以增加。",
    "unit": "天",
    "minimum": 7,
    "maximum": 365,
    "risk_level": "low",
    "restart_required": false
  }
}
```

---

## 7. P1 实施要求

P1 UI 模块化必须先建立：

- `SettingsPage`；
- `SettingField`；
- `SettingHelp`；
- `SettingStatusBadge`；
- `SettingsSearch`；
- `SettingsGroupNavigation`；
- `ImpactPreviewDialog` 接口；
- `useSettings` Hook；
- 统一 `SettingDefinition` 类型。

现有设置页面必须保留并增强：

- 默认值；
- 当前值；
- 已覆盖状态；
- 恢复默认；
- 搜索；
- 只显示已修改；
- 参数范围；
- 说明。

P2-P7 新增任何可配置默认值时，必须先进入 Setting Registry，再开发对应业务逻辑和 UI。

---

## 8. 验收标准

每个含默认值的模块必须增加自动测试：

1. 后端默认值存在；
2. UI 能找到该设置；
3. UI 显示当前值和默认值；
4. 修改后保存并生效；
5. 单项恢复默认；
6. 分组恢复默认；
7. 非法范围被拒绝；
8. 高风险设置出现影响预览；
9. 设置说明非空；
10. 无 GPU、Provider 不可用或功能禁用时仍显示设置和禁用原因；
11. 前端不得重复硬编码后端默认值；
12. 模块报告列出全部新增默认值和 UI 路径。

未满足以上规则，不得标记模块 `ACCEPTED`。

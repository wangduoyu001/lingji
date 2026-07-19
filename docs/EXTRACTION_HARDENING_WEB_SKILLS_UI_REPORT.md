# 灵机提取加固、网站采集、Skill 注册与 Obsidian UI 开发报告

## 1. 本阶段目标

本阶段不是继续堆入口文件夹，而是解决统一提取框架真正上线前的安全、并发、版本、隐私、交互和可维护性问题，并建立网页与社交平台的通用采集底座。

完成范围：

1. SQLite 提取队列加固。
2. 人工审批和人工备注保护。
3. ChatGPT 导入安全限制与敏感内容分流。
4. Codex 多次执行的版本化写回。
5. 普通网站、公众号、视频号、抖音和小红书的统一采集适配器。
6. Obsidian 提取中心、Bases、模板和本地操作插件。
7. Skill 注册中心。
8. Linux、Windows、MCP 和 Obsidian 插件 CI。

## 2. 设计原则

### 2.1 单一权威来源

| 内容 | 权威位置 |
|---|---|
| 正式知识、项目、任务、决策、来源笔记 | Obsidian Vault |
| 提取队列、租约、处理状态、审计 | `storage/lingji_state.db` |
| 可重建全文召回索引 | `storage/lingji_memory.db` |
| 原始输入快照 | `storage/raw/` |
| 历史生成版本 | `storage/versions/` |
| Skill 可执行代码、配置和测试 | Git 或原安装目录 |
| Skill 清单、状态、说明和验证记录 | Obsidian `07-Assets/Skills/` |

Obsidian 不复制整套 Skill 代码。复制代码会产生多个权威副本，后续更新、依赖和安全修复会失去同步依据。

### 2.2 平台权限边界

- 不偷取浏览器 Cookie。
- 不绕过登录、付费、私密群或平台权限。
- 服务端网络抓取默认关闭。
- 动态或登录态页面优先由浏览器插件、手机分享、页面快照、录屏或本地媒体主动投喂。
- 只有链接且无法取得正文时，保存元数据并标记 `needs_review`，而不是伪造“完整提取成功”。

## 3. SQLite 队列加固

文件：

```text
src/extraction/queue.py
src/extraction/pipeline.py
```

新增字段：

```text
adapter_version
lease_token
heartbeat_at
progress_current
progress_total
progress_message
```

### 3.1 幂等

幂等键现在包含：

```text
source_type
adapter_name
adapter_version
input content identity
payload
options
```

同一份 ChatGPT 导出使用不同项目或隐私选项时，不会错误复用旧任务。

`force` 重跑会刷新：

- 来源类型。
- 适配器和版本。
- 输入路径。
- Payload。
- Options。
- 优先级。
- 最大重试次数。
- 进度、错误和旧结果。

### 3.2 租约和心跳

Worker 领取任务时生成 `lease_token`。处理期间后台心跳续租。

完成或失败必须同时匹配：

```text
job_id
locked_by
lease_token
status=running
```

旧 Worker 在任务被重新领取后不能覆盖新 Worker 的结果。

## 4. 原始快照与版本保护

### 4.1 文件输入

保存到：

```text
storage/raw/<source_type>/<sha256>/<filename>
```

### 4.2 目录输入

目录不再只保存清单。现在同时生成：

```text
storage/raw/<source_type>/<sha256>/directory_manifest.json
storage/raw/<source_type>/<sha256>/directory_snapshot.zip
```

删除原始目录后仍可恢复。

### 4.3 派生笔记历史

提取器覆盖旧生成内容前，会保存旧版本：

```text
storage/versions/<stable_id>/<old_content_hash>.md
```

### 4.4 人工内容保护

重新提取时保护：

```text
owner_confirmed
review_status
pin_to_context
importance
valid_from
valid_to
supersedes
superseded_by
agent_scope
manual_notes
```

已由主人确认的笔记还会保留人工 `status`。

标签、项目和关系采用合并，而不是覆盖。

人工正文写在：

```text
<!-- LINGJI:MANUAL:START -->
## 人工备注
...
<!-- LINGJI:MANUAL:END -->
```

## 5. 敏感内容分流

文件：

```text
src/extraction/privacy.py
```

当前本地检测：

- API Key、Token、Secret。
- 私钥。
- 密码字段。
- 中国身份证号。
- 银行卡号。
- 手机号。
- 邮箱。
- 用户定义敏感词。

高风险资料进入：

```text
08-Private/Imports/<source_type>/YYYY/MM/
```

`08-Private` 默认不进入普通索引。

注意：敏感检测不是加密。原始快照加密、密钥管理和备份加密仍属于后续安全阶段。

## 6. ChatGPT 导入器

适配器：

```text
chatgpt_export 1.1.0
```

新增安全限制：

- ZIP JSON 文件数量。
- 单个 ZIP 成员大小。
- ZIP 总解压大小。
- 压缩比。
- 最大对话数量。
- 单个 JSON 文件大小。
- 限制读取长度。

每个对话单独执行敏感分类。高风险对话进入 `08-Private/Imports/chatgpt`。

当前仍然以 JSON 文件为单位加载。对于数百 MB 的单个 JSON，虽然已有大小上限，但真正的增量 JSON 流式解析仍应作为后续大数据优化。

## 7. Codex 写回

适配器：

```text
codex_work_report 1.1.0
```

工作报告稳定 ID：

```text
LJ-CODEX-<task_id>-<execution_id>
```

错误、决策和任务使用内容哈希：

```text
LJ-ERROR-<task>-<content_hash>
LJ-DECISION-<task>-<content_hash>
LJ-TASK-<task>-<content_hash>
```

同一任务的多次执行不会覆盖旧报告；列表插入新项目也不会导致后续子项 ID 整体错位。

## 8. 通用网页和社交平台采集

适配器：

```text
web_capture 1.0.0
```

支持输入：

- URL。
- HTML。
- 浏览器选中文字。
- 页面正文。
- 标题。
- 作者或账号。
- 简介。
- 发布时间。
- 视频时长。
- 封面。
- 媒体 URL 或本地媒体路径。
- 视频或音频转写。
- OCR 文本。
- JSON 快照。

### 8.1 平台矩阵

| 平台 | 当前能力 | 完整程度 |
|---|---|---|
| 普通静态网页 | HTML、正文、Meta、OpenGraph、Canonical、选中文字 | 已实现基础版本 |
| 公众号文章 | 链接、浏览器 HTML、标题、作者、发布时间、正文、封面 | 已实现主动投喂路径 |
| 视频号 | 链接、账号、简介、发布时间、时长、封面、转写、OCR、本地媒体引用 | 已实现降级采集，不绕登录态 |
| 抖音 | 链接、页面快照、账号、标题、简介、封面、转写、OCR、本地媒体 | 已实现统一入口，未实现登录态自动化 |
| 小红书 | 链接、页面快照、作者、正文、图片/封面引用、OCR | 已实现统一入口，未实现登录态自动化 |
| Bilibili | 通用网页元数据、正文、转写和媒体引用 | 通用支持 |
| YouTube | 通用网页元数据、正文、转写和媒体引用 | 通用支持 |
| 其他网站 | URL、HTML、Meta、正文、选中文字 | 通用支持 |

### 8.2 视频号说明

视频号分享页面可能只暴露有限元数据。系统不会将“仅拿到链接”标成完整成功。

建议采集链路：

```text
手机或浏览器分享
  ↓
链接 + 账号 + 简介 + 页面快照
  ↓
有本地视频或录屏时补充媒体路径
  ↓
媒体处理器生成转写、关键帧和 OCR
  ↓
web_capture 统一写入来源笔记
```

本阶段已经支持承接转写、OCR、封面和媒体引用，但自动运行 FFmpeg、ASR、说话人分离、场景切分和关键帧 OCR 的 `MediaExtractionAdapter` 尚未开发完成。

### 8.3 安全网络抓取

服务端抓取默认：

```text
WEB_NETWORK_FETCH_ENABLED=false
```

启用后仍会限制：

- 仅 HTTP/HTTPS。
- 阻止 localhost。
- 阻止私网、回环、链路本地和保留地址。
- 跳转后再次校验。
- 请求超时。
- 最大响应字节数。

## 9. Obsidian 文件结构

本阶段新增或重点使用：

```text
00-System/
├── Extraction-Center.md
├── Skills-Center.md
├── Extraction/
│   └── Requests/
├── Bases/
│   ├── Extraction Sources.base
│   ├── Extraction Requests.base
│   ├── Work Reports.base
│   └── Skills.base
└── Templates/
    ├── ChatGPT导入请求.md
    ├── 网页与视频号采集请求.md
    └── Skill同步请求.md

02-Sources/
├── Conversations/ChatGPT/
└── Web/
    ├── Websites/
    ├── WeChat-Articles/
    ├── Video-Channels/
    ├── Douyin/
    └── Xiaohongshu/

05-Operations/
├── Work-Reports/
├── Errors/
├── Decisions/Candidates/
└── Tasks/Inbox/

07-Assets/
└── Skills/

08-Private/
└── Imports/
```

## 10. Obsidian UI

### 10.1 原生页面和 Bases

`LingJiSystemUI` 自动生成：

- 提取中心。
- Skill 管理中心。
- 采集来源视图。
- 缺失正文和需要补采视图。
- 敏感来源视图。
- Codex 工作报告视图。
- Skill 可用、待验证和停用视图。
- Obsidian 采集请求队列。

### 10.2 LingJi Control 插件

目录：

```text
obsidian-plugin/lingji-control/
```

提供：

- 侧边栏灵机按钮。
- 打开提取中心。
- 打开 Skill 中心。
- 新建 ChatGPT 导入请求。
- 新建网页或视频号采集请求。
- 新建 Skill 同步请求。
- 网页采集请求可读取剪贴板中的链接或文字。

安装：

```powershell
python scripts/install_obsidian_plugin.py --vault "E:\obsidian\本地知识库"
```

然后在 Obsidian 设置的社区插件页面启用 `LingJi Control`。

插件创建的请求默认是 `draft`。主人确认后将 `status` 改为 `queued`，后台服务才会执行。

## 11. Skill 管理原则

结论：Skill 应统一由 Obsidian 管理，但只管理控制信息，不把 Obsidian 变成代码仓库。

Obsidian 保存：

- 名称和说明。
- 版本。
- 状态和审核状态。
- 能力和触发条件。
- 依赖。
- 兼容 Agent。
- 源路径和仓库。
- 入口命令。
- 测试命令和验证时间。
- 关联项目和人工备注。

Git 或安装目录保存：

- 源代码。
- 可执行脚本。
- 依赖锁文件。
- 单元测试。
- 发布包。
- 安全更新历史。

同步：

```powershell
python scripts/sync_skills.py "D:\codex\skills"
```

## 12. 使用入口

### 12.1 网页与视频号 CLI

```powershell
python scripts/capture_web_source.py "https://example.com" --platform web --project LingJi
```

视频号：

```powershell
python scripts/capture_web_source.py "<分享链接>" `
  --platform video_channel `
  --account-name "账号名称" `
  --description "视频简介" `
  --transcript-file "D:\capture\transcript.txt" `
  --project LingJi
```

### 12.2 MCP

新增：

```text
capture_web_source
register_skill
sync_skill_directory
list_skills
```

### 12.3 Obsidian

使用 `LingJi Control` 命令或打开：

```text
00-System/Extraction-Center.md
00-System/Skills-Center.md
```

## 13. CI 和测试

CI 矩阵：

- Ubuntu Python 3.11。
- Ubuntu Python 3.12。
- Windows Python 3.12。
- MCP Server 创建。
- Obsidian 插件 JavaScript 与 manifest 校验。

新增测试覆盖：

- Options 参与幂等。
- 强制重跑参数。
- 租约令牌。
- 人工审批和人工备注保护。
- ChatGPT 安全限制和隐私分流。
- Codex 多次执行历史。
- 视频号和网页采集。
- 敏感网页分流。
- HTML 元数据和正文解析。
- Skill 注册、同步和人工状态保护。
- Obsidian Bases、模板和请求处理。

## 14. 仍未完成的功能

本阶段不应被描述为“所有平台已经百分之百自动提取”。尚需开发：

1. FFmpeg 音视频元数据、音轨提取和转码。
2. 本地或云端 ASR。
3. 说话人分离。
4. 场景切分和关键帧。
5. 关键帧 OCR 和视觉描述。
6. 视频时间码索引。
7. 浏览器扩展的完整页面快照与项目选择 UI。
8. Playwright 动态页面采集服务。
9. 手机快捷指令、Android 分享目标和断点上传。
10. 原始快照加密、密钥管理、容量限制和冷归档。
11. 真实视频号、抖音、小红书账号端到端验收。
12. 大型单 JSON 的真正流式解析。

## 15. 下一阶段建议

顺序：

```text
MediaExtractionAdapter
  ↓
浏览器扩展 / Playwright Capture
  ↓
手机分享 API
  ↓
GitHub 专用同步适配器
  ↓
微信授权导入器
  ↓
原始资料加密和容量管理
```

这套顺序基于已完成的统一 Adapter、Queue、Sink、隐私边界和 Obsidian UI，后续入口只扩展适配器，不再重构底座。

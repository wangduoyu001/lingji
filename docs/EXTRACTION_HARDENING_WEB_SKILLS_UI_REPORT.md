# 灵机提取加固、网站采集、媒体处理、Skill 与 Obsidian UI 开发报告

## 1. 本阶段目标

本阶段解决统一提取框架上线前的安全、并发、版本、隐私和交互问题，并建立网页、社交平台、本地音视频和 Skill 的统一管理入口。

已完成：

1. SQLite 提取队列加固。
2. 人工审批、人工备注和历史版本保护。
3. ChatGPT 导入安全限制与敏感内容分流。
4. Codex 多次执行的版本化写回。
5. 普通网站、公众号、视频号、抖音、小红书等通用采集适配器。
6. 本地音视频元数据、可选音轨与关键帧适配器。
7. Obsidian 提取中心、Bases、请求队列和本地插件。
8. Skill 注册中心。
9. Linux、Windows、MCP 和 Obsidian 插件 CI。

## 2. 权威数据位置

| 内容 | 权威位置 |
|---|---|
| 正式知识、项目、任务、决策和来源笔记 | Obsidian Vault |
| 提取队列、租约、处理状态和审计 | `storage/lingji_state.db` |
| 可重建召回索引 | `storage/lingji_memory.db` |
| 原始输入快照 | `storage/raw/` |
| 自动生成笔记旧版本 | `storage/versions/` |
| 媒体派生音轨和关键帧 | `storage/derived/media/` |
| Skill 可执行代码、依赖和测试 | Git 或原安装目录 |
| Skill 清单、状态、说明和验证记录 | `07-Assets/Skills/` |

## 3. SQLite 队列加固

新增或强化：

```text
adapter_version
lease_token
heartbeat_at
progress_current
progress_total
progress_message
```

幂等键包含：

```text
source_type
adapter_name
adapter_version
input identity
payload
options
```

同一份 ChatGPT 导出使用不同项目或隐私选项时，不会错误复用旧任务。

Worker 完成或失败必须匹配：

```text
job_id
locked_by
lease_token
status=running
```

旧 Worker 在任务被重新领取后不能覆盖新 Worker 的结果。

## 4. 原始快照与人工内容保护

### 4.1 文件输入

```text
storage/raw/<source_type>/<sha256>/<filename>
```

### 4.2 目录输入

```text
storage/raw/<source_type>/<sha256>/directory_manifest.json
storage/raw/<source_type>/<sha256>/directory_snapshot.zip
```

目录清单不再冒充备份。

### 4.3 历史版本

自动生成笔记被更新前保存到：

```text
storage/versions/<stable_id>/<old_content_hash>.md
```

### 4.4 保护字段

重新提取时保留：

```text
owner_confirmed
review_status
status（主人已确认时）
pin_to_context
importance
valid_from
valid_to
supersedes
superseded_by
agent_scope
manual_notes
tags
related
project
```

人工正文位于：

```text
<!-- LINGJI:MANUAL:START -->
## 人工备注
...
<!-- LINGJI:MANUAL:END -->
```

## 5. 敏感内容分流

本地检测：

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

注意：敏感分类不是磁盘加密。密钥管理和加密备份仍属于后续安全阶段。

## 6. ChatGPT 导入

适配器：

```text
chatgpt_export 1.1.0
```

支持：

- 官方导出 ZIP。
- `conversations.json`。
- 编号 conversation JSON。
- 已解压目录。

安全限制：

- ZIP JSON 文件数量。
- 单成员大小。
- 总解压大小。
- 压缩比。
- 最大对话数量。
- 单 JSON 文件大小。
- 限制读取长度。

每个对话独立执行敏感分类。高风险对话进入 `08-Private/Imports/chatgpt`。

当前大型单 JSON 仍按文件读取，真正流式 JSON 解析尚未实现。

## 7. Codex 写回

适配器：

```text
codex_work_report 1.1.0
```

工作报告 ID：

```text
LJ-CODEX-<task_id>-<execution_id>
```

子项 ID：

```text
LJ-ERROR-<task>-<content_hash>
LJ-DECISION-<task>-<content_hash>
LJ-TASK-<task>-<content_hash>
```

同一任务的多次执行不会覆盖旧报告，列表顺序变化也不会让子项 ID 集体错位。

## 8. 网页与社交平台采集

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
- 转写。
- OCR。
- JSON 页面快照。

### 8.1 平台矩阵

| 平台 | 当前能力 | 状态 |
|---|---|---|
| 普通静态网页 | HTML、正文、Meta、OpenGraph、Canonical、选中文字 | 基础完成 |
| 公众号文章 | 链接、浏览器 HTML、标题、作者、发布时间、正文、封面 | 主动投喂路径完成 |
| 视频号 | 链接、账号、简介、发布时间、时长、封面、转写、OCR、本地媒体引用 | 降级采集完成 |
| 抖音 | 链接、页面快照、账号、标题、简介、封面、转写、OCR、本地媒体 | 统一入口完成，登录态自动化未完成 |
| 小红书 | 链接、页面快照、作者、正文、封面引用、OCR | 统一入口完成，登录态自动化未完成 |
| Bilibili | 通用网页元数据、正文、转写和媒体引用 | 通用支持 |
| YouTube | 通用网页元数据、正文、转写和媒体引用 | 通用支持 |
| 其他网站 | URL、HTML、Meta、正文、选中文字 | 通用支持 |

只有链接而没有正文时：

```yaml
content_completeness: metadata_only
status: needs_review
```

系统不会把有限元数据冒充完整提取。

### 8.2 网络抓取安全

默认：

```text
WEB_NETWORK_FETCH_ENABLED=false
```

启用后仍限制：

- 仅 HTTP/HTTPS。
- 阻止 localhost。
- 阻止私网、回环、链路本地和保留地址。
- 跳转后重新校验。
- 请求超时。
- 最大响应大小。

动态或登录态平台必须由主人主动分享、浏览器快照、录屏或本地媒体投喂，不偷取 Cookie。

## 9. 本地音视频处理

适配器：

```text
media_local 1.0.0
```

已实现：

- 视频和音频文件识别。
- SHA-256 和原始快照。
- FFprobe 容器、时长、码率、编码、分辨率、帧率、采样率和声道。
- 可选 FFmpeg 单声道 16kHz WAV 音轨。
- 可选限量关键帧。
- 接入已有转写、OCR 和视觉描述。
- 缺少语义资料时标记 `metadata_only / needs_review`。
- 敏感转写和 OCR 进入私密目录。

详细文档：

```text
docs/MEDIA_EXTRACTION_REPORT.md
```

尚未实现：

- ASR Provider。
- 说话人分离。
- 自动 OCR Provider。
- 视觉模型描述。
- 镜头、人物、动作和场景识别。
- 网页来源与本地媒体自动配对。

## 10. Obsidian 文件结构

```text
00-System/
├── Extraction-Center.md
├── Skills-Center.md
├── Extraction/Requests/
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
├── Web/
│   ├── Websites/
│   ├── WeChat-Articles/
│   ├── Video-Channels/
│   ├── Douyin/
│   └── Xiaohongshu/
├── Videos/
└── Audios/

05-Operations/
├── Work-Reports/
├── Errors/
├── Decisions/Candidates/
└── Tasks/Inbox/

07-Assets/Skills/
08-Private/Imports/
```

## 11. Obsidian UI

`LingJiSystemUI` 生成：

- 提取中心。
- Skill 管理中心。
- 采集来源视图。
- 缺失正文和补采视图。
- 敏感来源视图。
- Codex 工作报告视图。
- Skill 可用、待验证和停用视图。
- 提取请求队列。

`LingJi Control` 插件提供：

- 侧边栏入口。
- 打开提取中心。
- 打开 Skill 中心。
- 新建 ChatGPT 导入请求。
- 新建网页或视频号采集请求。
- 新建本地音视频提取请求。
- 新建 Skill 同步请求。

插件创建的请求默认 `draft`。主人确认后改为 `queued`，后台服务才执行。

安装：

```powershell
python scripts/install_obsidian_plugin.py --vault "E:\obsidian\本地知识库"
```

## 12. Skill 管理

结论：Skill 应由 Obsidian 统一管理，但 Obsidian 只做控制平面。

Obsidian 保存：

- 名称、说明和版本。
- 状态和审核状态。
- 能力和触发条件。
- 依赖和兼容 Agent。
- 源路径、仓库和入口命令。
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

## 13. 使用入口

```text
scripts/import_chatgpt_export.py
scripts/submit_codex_report.py
scripts/capture_web_source.py
scripts/process_media.py
scripts/sync_skills.py
```

MCP：

```text
enqueue_chatgpt_export
submit_codex_work_report
capture_web_source
register_skill
sync_skill_directory
list_skills
extraction_job_status
extraction_queue_status
process_extraction_jobs
```

## 14. 测试

GitHub Actions 当前覆盖：

- Ubuntu Python 3.11。
- Ubuntu Python 3.12。
- Windows Python 3.12。
- Python 编译检查。
- MCP Server 创建。
- Obsidian 插件 JavaScript 和 manifest。

最新结果：

```text
Ran 72 tests
OK
```

## 15. 仍需完成

1. 真实 `E:\obsidian\本地知识库` 快照与迁移验收。
2. 真实 ChatGPT 导出包脱敏测试。
3. 真实视频号、抖音和小红书主动投喂测试。
4. 浏览器扩展完整快照和项目选择 UI。
5. Playwright 动态页面采集服务。
6. 手机快捷指令和 Android 分享入口。
7. ASR、说话人分离、自动 OCR 和视觉模型 Provider。
8. 原始快照加密、容量限制、冷归档和磁盘预警。
9. 大型单 JSON 流式解析。

# 实施设计：任务① WorkBuddy 接入

> 状态：DESIGNED。目标：灵机"能拿到所有信息"清单的下一个成员——腾讯
> WorkBuddy（本机数据 ~2.6GB / 5 万文件，含会话与审计 JSONL）。

## 数据勘察结论（已实地勘察 ~/.workbuddy）

| 数据 | 路径 | 形态 |
| --- | --- | --- |
| 会话索引 | app/sessions.json | JSON：conversationId/workDir/startedAt/resumedAt |
| 会话正文 | sessions/*.json、workspace/sessions/、app/session/ | 待细察（任务第一步） |
| 审计日志 | audit-log/YYYY-MM-DD.jsonl | JSONL：工具调用/命令/决策（含 commandPreview） |
| 身份/记忆 | IDENTITY.md/MEMORY.md/USER.md | Markdown |

## 切片

1. **格式勘察**（半天）：确定会话正文的确切 schema（消息角色/时间/内容字段）。
2. **适配器** `src/extraction/adapters/workbuddy.py`：
   - source_type `workbuddy_session`
   - 输入：授权根 = `~/.workbuddy`
   - 输出：StructuredSource（对话/消息/时间戳），复用统一脱敏接缝。
3. **清单升级**：kind=workbuddy 从 `supported=False` → session_read 能力开启
   （发现→授权→导入链路与 Codex 完全一致）。
4. **隐私分级**：WorkBuddy 审计日志含命令与路径痕迹——默认 private，
   云端提炼对 WorkBuddy 来源默认跳过（本地提炼不受限），后续可主人放开。

## 依赖与顺序

- 无阻塞依赖；建议排在任务③（手机捕获）与任务②（历史清洗）之后，
  因为②的清洗基线会直接让 WorkBuddy 导入即合规。

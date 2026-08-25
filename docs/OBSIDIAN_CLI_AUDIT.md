# Obsidian CLI 审计报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

**审计时间**: 2026-07-19 01:00
**Git 分支**: feature/second-brain-memory

---

## 1. 环境检查

### 1.1 系统信息
- 操作系统: Windows
- Shell: PowerShell
- 项目根: D:/codex/lingji-second-brain

### 1.2 Git 状态
- 分支: feature/second-brain-memory
- 工作区: 干净

### 1.3 Obsidian 桌面版
- 状态: 已安装 (v1.12.7)
- 路径: D:\\Program Files (x86)\\Obsidian\\Obsidian.exe
- 运行中: 是

### 1.4 Obsidian CLI (Obsidian.com)
- 路径: D:\\Program Files (x86)\\Obsidian\\Obsidian.com
- 版本: 1.12.7
- PATH 注册: 否 (需完整路径)

### 1.5 Vault
- 名称: 本地知识库
- 路径: E:\\obsidian\\本地知识库
- 类型: 单 Vault

---

## 2. CLI 命令验证

| 命令 | 状态 | 结果 |
|------|------|------|
| version | ✅ | 1.12.7 |
| help | ✅ | 全部命令可用 |
| vaults verbose | ✅ | 1 个 Vault |
| search "灵机" | ✅ | 88 条 |
| search "AI" | ✅ | 多条 |
| tags | ✅ | 260 个标签 |
| tasks | ✅ | 无任务 |
| daily:read | ✅ | 未创建 |
| read Control Center | ✅ | 内容正确 |
| files PEMIS ext=.md | ✅ | 91 个文件 |

---

## 3. 结论

所有 CLI 操作正常。可在 vault 中创建测试笔记。

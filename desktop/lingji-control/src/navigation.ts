import type { NavigationGroup, NavigationItem } from "./types";

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  { id: "observe", label: "日常使用" },
  { id: "advanced", label: "高级诊断" },
];

export const PRIMARY_NAVIGATION: NavigationItem[] = [
  { id: "overview", label: "首页", hint: "查看灵机是否正常，以及你是否需要做事", group: "observe", icon: "home" },
  { id: "memory_cards", label: "记忆内容", hint: "查看具体记忆、来源和处理状态", group: "observe", icon: "inspect" },
  { id: "attention", label: "需要我", hint: "只显示现在需要你决定的事项", group: "observe", icon: "review" },
  { id: "memory_sources", label: "记忆来源", hint: "选择灵机要记住的内容", group: "observe", icon: "vault" },
];

export const ADVANCED_NAVIGATION: NavigationItem[] = [
  { id: "brain_status", label: "脑状态", hint: "记忆、模型、算力与任务详细状态", group: "advanced", icon: "pulse" },
  { id: "codex_workspace", label: "项目与对话", hint: "项目、会话、当前工作与处理进度", group: "advanced", icon: "project" },
  { id: "activity", label: "活动记录", hint: "查看灵机最近完成的工作", group: "advanced", icon: "logs" },
  { id: "memory_review", label: "人工记忆审核", hint: "主人批准、编辑或拒绝候选记忆", group: "advanced", icon: "review" },
  { id: "auto_review", label: "自动审查 SHADOW", hint: "查看建议、风险与解释，不执行变更", group: "advanced", icon: "shield" },
  { id: "memory_inspector", label: "记忆检查器", hint: "来源、对话、消息与记忆关系", group: "advanced", icon: "inspect" },
  { id: "obsidian", label: "Obsidian", hint: "Vault、状态与安全操作", group: "advanced", icon: "vault" },
  { id: "capture_center", label: "手动投喂中心", hint: "主动投喂：提交文本、网页、文件与媒体到正式采集队列", group: "advanced", icon: "capture" },
  { id: "media", label: "媒体分析", hint: "转写、OCR、镜头与语义摘要", group: "advanced", icon: "media" },
  { id: "jobs", label: "任务队列明细", hint: "提取任务、重试和失败细节", group: "advanced", icon: "queue" },
  { id: "vector_center", label: "向量中心", hint: "Embedding、Qdrant 与索引覆盖率", group: "advanced", icon: "vector" },
  { id: "system_compute", label: "系统与算力", hint: "CPU、GPU、显存与运行模式", group: "advanced", icon: "compute" },
  { id: "models", label: "AI 与模型", hint: "模型清单、用途、兼容状态与 API 入口", group: "advanced", icon: "model" },
  { id: "storage", label: "存储", hint: "容量、冷存储与恢复", group: "advanced", icon: "storage" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复", group: "advanced", icon: "backup" },
  { id: "acceptance", label: "环境验收", hint: "真实资料只读诊断", group: "advanced", icon: "acceptance" },
  { id: "settings", label: "设置", hint: "默认值、推荐值与主人覆盖", group: "advanced", icon: "settings" },
  { id: "logs", label: "日志", hint: "错误与运行记录", group: "advanced", icon: "logs" },
];

// Legacy direct routes remain addressable without becoming ordinary menu entries.
export const LEGACY_NAVIGATION: NavigationItem[] = [
  { id: "diagnostics", label: "高级诊断", hint: "遇到问题时查看详细信息", group: "advanced", icon: "settings" },
];

export const NAVIGATION: NavigationItem[] = [...PRIMARY_NAVIGATION, ...LEGACY_NAVIGATION, ...ADVANCED_NAVIGATION];

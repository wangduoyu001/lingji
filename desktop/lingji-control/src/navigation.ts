import type { NavigationGroup, NavigationItem } from "./types";

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  { id: "observe", label: "日常使用" },
  { id: "advanced", label: "高级" },
];

export const PRIMARY_NAVIGATION: NavigationItem[] = [
  { id: "overview", label: "首页", hint: "今天灵机替你做了什么，以及你现在是否需要行动", group: "observe", icon: "home" },
  { id: "memory", label: "记忆", hint: "查看灵机真正记住了什么、来源和可验证状态", group: "observe", icon: "inspect" },
  { id: "activity", label: "工作", hint: "查看灵机当前工作、完成结果和自动重试", group: "observe", icon: "project" },
  { id: "attention", label: "需要我", hint: "只显示有真实对象、必须由你决定的事项", group: "observe", icon: "review" },
  { id: "diagnostics", label: "高级", hint: "数据源、模型、向量、存储、设置和诊断", group: "observe", icon: "settings" },
];

export const ADVANCED_NAVIGATION: NavigationItem[] = [
  { id: "brain_status", label: "脑状态", hint: "记忆、模型、算力与任务详细状态", group: "advanced", icon: "pulse" },
  { id: "codex_workspace", label: "Codex 工作记录", hint: "本机识别到的项目、工作会话、进度与上下文", group: "advanced", icon: "project" },
  { id: "memory_review", label: "永久记忆审核", hint: "批准、编辑或拒绝长期记忆候选", group: "advanced", icon: "review" },
  { id: "auto_review", label: "自动审查 SHADOW", hint: "查看建议、风险与解释，不执行变更", group: "advanced", icon: "shield" },
  { id: "memory_inspector", label: "记忆来源检查", hint: "来源、工作记录、消息与记忆关系", group: "advanced", icon: "inspect" },
  { id: "obsidian", label: "Obsidian", hint: "Vault、状态与安全操作", group: "advanced", icon: "vault" },
  { id: "capture_center", label: "添加资料", hint: "手工添加文字、网页、文件、媒体和历史导出", group: "advanced", icon: "capture" },
  { id: "capture", label: "采集兼容入口", hint: "旧版网页、文字与本地文件入口", group: "advanced", icon: "feed" },
  { id: "media", label: "媒体分析", hint: "转写、OCR、镜头与语义摘要", group: "advanced", icon: "media" },
  { id: "jobs", label: "任务队列", hint: "提取任务、重试和失败细节", group: "advanced", icon: "queue" },
  { id: "vector_center", label: "向量中心", hint: "Embedding、Qdrant 与索引覆盖率", group: "advanced", icon: "vector" },
  { id: "system_compute", label: "系统与算力", hint: "CPU、GPU、显存与运行模式", group: "advanced", icon: "compute" },
  { id: "models", label: "AI 与模型", hint: "模型清单、用途、兼容状态与 API 入口", group: "advanced", icon: "model" },
  { id: "storage", label: "存储", hint: "容量、冷存储与恢复", group: "advanced", icon: "storage" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复", group: "advanced", icon: "backup" },
  { id: "acceptance", label: "环境验收", hint: "真实资料只读诊断", group: "advanced", icon: "acceptance" },
  { id: "settings", label: "设置", hint: "默认值、推荐值与主人覆盖", group: "advanced", icon: "settings" },
  { id: "logs", label: "原始日志", hint: "错误与运行记录，仅用于诊断", group: "advanced", icon: "logs" },
];

export const NAVIGATION: NavigationItem[] = [...PRIMARY_NAVIGATION, ...ADVANCED_NAVIGATION];

import type { NavigationGroup, NavigationItem } from "./types";

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  { id: "home", label: "总览" },
  { id: "memory", label: "记忆与项目" },
  { id: "ingestion", label: "采集与处理" },
  { id: "runtime", label: "模型与运行" },
  { id: "operations", label: "运维与设置" },
];

export const NAVIGATION: NavigationItem[] = [
  { id: "overview", label: "控制总览", hint: "状态、任务、存储与预警", group: "home" },
  { id: "brain_status", label: "脑状态", hint: "记忆、模型、算力与任务一屏总览", group: "home" },

  { id: "codex_workspace", label: "项目与对话", hint: "项目、会话、当前工作与处理进度", group: "memory" },
  { id: "memory_review", label: "人工记忆审核", hint: "主人批准、编辑或拒绝候选记忆", group: "memory" },
  { id: "auto_review", label: "自动审查 SHADOW", hint: "查看建议、风险与解释，不执行变更", group: "memory" },
  { id: "memory_inspector", label: "记忆检查器", hint: "来源、对话、消息与记忆关系", group: "memory" },
  { id: "obsidian", label: "Obsidian", hint: "Vault、状态与安全操作", group: "memory" },

  { id: "capture_center", label: "手动投喂中心", hint: "提交文本、网页、文件与媒体到正式采集队列", group: "ingestion" },
  { id: "capture", label: "主动投喂", hint: "网页、文字与本地文件", group: "ingestion" },
  { id: "media", label: "媒体分析", hint: "转写、OCR、镜头与语义摘要", group: "ingestion" },
  { id: "jobs", label: "任务队列", hint: "提取任务与重试情况", group: "ingestion" },

  { id: "vector_center", label: "向量中心", hint: "Embedding、Qdrant 与索引覆盖率", group: "runtime" },
  { id: "system_compute", label: "系统与算力", hint: "CPU、GPU、显存与运行模式", group: "runtime" },
  { id: "models", label: "AI 与模型", hint: "模型清单、用途、兼容状态与 API 入口", group: "runtime" },

  { id: "storage", label: "存储", hint: "容量、冷存储与恢复", group: "operations" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复", group: "operations" },
  { id: "acceptance", label: "环境验收", hint: "真实资料只读诊断", group: "operations" },
  { id: "settings", label: "设置", hint: "默认值、推荐值与主人覆盖", group: "operations" },
  { id: "logs", label: "日志", hint: "错误与运行记录", group: "operations" },
];

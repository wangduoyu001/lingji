import type { NavigationGroup, NavigationItem } from "./types";

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  { id: "observe", label: "日常使用" },
  { id: "advanced", label: "高级诊断" },
];

export const PRIMARY_NAVIGATION: NavigationItem[] = [
  { id: "overview", label: "首页", hint: "灵机正在干什么、刚刚做了什么、一切是否正常", group: "observe", icon: "home" },
  { id: "memory_library", label: "记忆库", hint: "灵机记住的全部内容：自动提炼+永久记忆，每条可打开", group: "observe", icon: "inspect" },
  { id: "memory_sources", label: "原始数据", hint: "扫描到的全部记录：来源、文件、每条对话原文", group: "observe", icon: "vault" },
  { id: "timeline_page", label: "时间线", hint: "按天看记忆的变化：新发现/入库/更新", group: "observe", icon: "logs" },
  { id: "work_ledger", label: "工作记录", hint: "灵机的每一次检查：每一步处理了多少、结果如何", group: "observe", icon: "logs" },
  { id: "memory_cards", label: "提炼候选", hint: "灵机提炼出的要点卡，支持批量转入永久记忆", group: "observe", icon: "inspect" },
  { id: "changes_ledger", label: "变更账本", hint: "第二大脑的每一笔变化，按时间排列", group: "observe", icon: "logs" },
  { id: "processing_detail", label: "处理详情", hint: "扫描/提炼/候选/记忆/时间线/向量 各环节数据", group: "observe", icon: "pulse" },
];

export const ADVANCED_NAVIGATION: NavigationItem[] = [
  { id: "permanent_memory", label: "永久记忆(确认)", hint: "主人逐条确认过的长期记忆", group: "advanced", icon: "inspect" },
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
  { id: "attention", label: "需要我", hint: "只显示现在需要你决定的事项", group: "observe", icon: "review" },
];

export const NAVIGATION: NavigationItem[] = [...PRIMARY_NAVIGATION, ...LEGACY_NAVIGATION, ...ADVANCED_NAVIGATION];

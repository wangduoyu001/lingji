import type { NavigationItem } from "./types";

export const NAVIGATION: NavigationItem[] = [
  { id: "overview", label: "总览", hint: "状态与预警" },
  { id: "brain_status", label: "脑状态", hint: "记忆、模型、算力与任务" },
  { id: "memory_inspector", label: "记忆检查器", hint: "Source、Conversation、Message 与 Memory 关系" },
  { id: "vector_center", label: "向量中心", hint: "Embedding、Qdrant 与索引覆盖率" },
  { id: "system_compute", label: "系统与算力", hint: "CPU、GPU、显存与运行模式" },
  { id: "models", label: "AI 与模型", hint: "模型清单、用途和兼容状态" },
  { id: "jobs", label: "任务", hint: "采集与处理队列" },
  { id: "capture", label: "主动投喂", hint: "网页、文字和本地文件" },
  { id: "media", label: "媒体分析", hint: "转写、OCR 与镜头" },
  { id: "storage", label: "存储", hint: "容量、冷存储与恢复" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复" },
  { id: "acceptance", label: "环境验收", hint: "真实资料只读诊断" },
  { id: "settings", label: "设置", hint: "默认值、推荐值与主人覆盖" },
  { id: "logs", label: "日志", hint: "错误与运行记录" },
];

import type { LingJiApi } from "./api";

export type Row = Record<string, unknown>;

export type PageId =
  | "overview"
  | "brain_status"
  | "codex_workspace"
  | "memory_review"
  | "auto_review"
  | "memory_inspector"
  | "capture_center"
  | "obsidian"
  | "vector_center"
  | "system_compute"
  | "models"
  | "jobs"
  | "capture"
  | "media"
  | "storage"
  | "backups"
  | "acceptance"
  | "settings"
  | "logs";

export type NavigationGroupId = "home" | "memory" | "ingestion" | "runtime" | "operations";

export type NavigationItem = {
  id: PageId;
  label: string;
  hint: string;
  group: NavigationGroupId;
};

export type NavigationGroup = {
  id: NavigationGroupId;
  label: string;
};

export type PageProps = {
  api: LingJiApi;
  active: boolean;
};

export type RuntimeState =
  | "healthy"
  | "degraded"
  | "disabled"
  | "unavailable"
  | "configuration_required"
  | string;

export type RuntimeWarning = {
  code?: string;
  stage?: string;
  message?: string;
  [key: string]: unknown;
};

export type MemoryStatus = {
  as_of: string | null;
  source: "live" | "snapshot" | "unavailable" | string;
  stale: boolean;
  workspace: string | null;
  memory: Record<string, unknown>;
  vector: Record<string, unknown>;
  embedding: Record<string, unknown>;
  coverage: Record<string, unknown>;
  warnings: RuntimeWarning[];
  [key: string]: unknown;
};

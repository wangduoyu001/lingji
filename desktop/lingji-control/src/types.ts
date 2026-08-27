import type { LingJiApi } from "./api";

export type Row = Record<string, unknown>;

export type PageId =
  | "overview"
  | "memory_sources"
  | "activity"
  | "attention"
  | "diagnostics"
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

export type NavigationGroupId = "observe" | "advanced";

export type NavigationIcon =
  | "home"
  | "pulse"
  | "project"
  | "review"
  | "shield"
  | "inspect"
  | "vault"
  | "capture"
  | "feed"
  | "media"
  | "queue"
  | "vector"
  | "compute"
  | "model"
  | "storage"
  | "backup"
  | "acceptance"
  | "settings"
  | "logs";

export type NavigationItem = {
  id: PageId;
  label: string;
  hint: string;
  group: NavigationGroupId;
  icon: NavigationIcon;
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
  state: RuntimeState;
  documents: number | null;
  chunks: number | null;
  core_memories: number | null;
  revision: number | null;
  database_bytes: number | null;
  database_path: string | null;
  fts_tokenizer?: string | null;
  last_rebuild_at?: string | null;
  integrity?: {
    healthy?: boolean;
    error?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

export type EmbeddingStatus = {
  state?: string;
  provider_id?: string;
  configured_model?: string;
  primary_model?: string | null;
  fallback_model?: string | null;
  active_model?: string | null;
  dimension?: number | null;
  unavailable_models?: string[];
  request_count?: number;
  failure_count?: number;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  last_error?: string | null;
  verified?: boolean;
  available?: boolean;
  [key: string]: unknown;
};

export type VectorStatus = {
  as_of: string | null;
  source: string;
  stale: boolean;
  workspace: string | null;
  state: RuntimeState;
  ready: boolean;
  collection_exists: boolean;
  vectors: number | null;
  dimension: number | null;
  collection: string | null;
  mode: "embedded" | "remote" | "memory" | string | null;
  distance?: string | null;
  rebuild_required: boolean | null;
  last_error?: string | null;
  embedding: EmbeddingStatus;
  [key: string]: unknown;
};

export type VectorCoverage = {
  as_of: string | null;
  source: string;
  stale: boolean;
  workspace: string | null;
  state: RuntimeState;
  expected: number | null;
  indexed: number | null;
  missing: number | null;
  coverage: number | null;
  missing_chunk_ids: string[];
  missing_chunk_ids_truncated?: boolean;
  last_error?: string | null;
  [key: string]: unknown;
};

export type BrainStatusSummary = {
  memory_count?: number | null;
  memory_chunk_count?: number | null;
  memory_bytes?: number | null;
  memory_revision?: number | null;
  memory_state?: string | null;
  vector_count?: number | null;
  vector_state?: string | null;
  vector_collection?: string | null;
  vector_dimension?: number | null;
  vector_rebuild_required?: boolean | null;
  embedding_state?: string | null;
  embed_model?: string | null;
  workspace?: string | null;
  status_source?: string | null;
  status_stale?: boolean;
  status_as_of?: string | null;
  warnings?: RuntimeWarning[];
  [key: string]: unknown;
};

export type ObsidianIssueStatus = {
  code: string;
  message: string;
};

export type ObsidianStatus = {
  as_of?: string;
  state: RuntimeState;
  enabled: boolean;
  available: boolean;
  version?: string | null;
  vault_name?: string | null;
  cli_configured: boolean;
  vault_configured: boolean;
  cli_path_display: string;
  vault_path_display: string;
  cli_discovery_source: string;
  vault_discovery_source: string;
  timeout_seconds: number;
  dry_run: boolean;
  persisted?: boolean;
  capabilities: {
    status: boolean;
    read: boolean;
    write: boolean;
    dry_run: boolean;
    compatibility_forwarding: boolean;
  };
  issues: ObsidianIssueStatus[];
};

export type SettingDefinition = {
  group: string;
  label: string;
  description: string;
  type: "integer" | "number" | "boolean" | "string" | "choice";
  default: unknown;
  recommended?: unknown;
  recommendation_reason?: string;
  when_to_change?: string;
  minimum?: number;
  maximum?: number;
  choices?: string[];
  unit?: string;
  scope?: string;
  restart_required?: boolean;
  task_required?: boolean;
  risk_level?: "low" | "medium" | "high";
  cost_impact?: string;
  storage_impact?: string;
  performance_impact?: string;
  privacy_impact?: string;
  dependencies?: string[];
  conflicts?: string[];
  learn_more?: string;
  editable?: boolean;
};

export type SettingsSnapshot = {
  values: Record<string, unknown>;
  overrides: Record<string, unknown>;
  definitions: Record<string, SettingDefinition>;
};

export const SOURCE_STATES = [
  "detected",
  "consent_required",
  "authorized",
  "scanning",
  "scan_completed",
  "processing",
  "imported",
  "partial_failure",
  "empty",
  "current",
  "degraded",
  "unsupported",
  "revoked",
  "failed",
] as const;

export type SourceState = (typeof SOURCE_STATES)[number];

export type DiscoveredSource = {
  kind: string;
  display_name: string;
  candidate_root: string;
  status: string;
  capability?: string | null;
  reason?: string | null;
  file_count?: number | null;
  byte_count?: number | null;
  earliest_mtime?: number | null;
  latest_mtime?: number | null;
  format?: string | null;
  owner_action?: { kind?: string; label?: string; source_kind?: string } | null;
};

export type AuthorizedSource = {
  source_id: string;
  kind: string;
  root: string;
  status: string;
  capability?: string | null;
  policy_version?: string | null;
  grant_id?: string | null;
  granted_at?: string | null;
  expires_at?: string | null;
};

export type ScanRun = {
  scan_id: string;
  source_id: string;
  status: string;
  progress?: number | null;
  total?: number | null;
  queued?: number | null;
  reused?: number | null;
  updated?: number | null;
  skipped?: number | null;
  failed?: number | null;
  counts_present?: string[] | null;
  updated_at?: string | null;
  last_error?: string | null;
  processing_status?: string | null;
  processing_total?: number | null;
  processing_completed?: number | null;
  processing_failed?: number | null;
  processing_pending?: number | null;
  processing_counts_present?: string[] | null;
};

export type ScanDetailItem = {
  item_id: string;
  name?: string | null;
  source?: string | null;
  stage?: string | null;
  result?: string | null;
  reason?: string | null;
  updated_at?: string | null;
  retryable?: boolean | null;
  imported_sources?: number | null;
  imported_conversations?: number | null;
  imported_messages?: number | null;
};

export type ScanDetailResponse = ScanRun & {
  items?: ScanDetailItem[] | null;
  items_pagination?: {
    limit: number;
    offset: number;
    total: number | null;
    has_more: boolean;
  } | null;
};

export type ScanSummary = {
  counts?: Record<string, number | null>;
  total?: number | null;
  latest?: ScanRun | null;
  progress?: { current?: number | null; total?: number | null } | null;
  last_error?: string | null;
  next_action?: string | null;
};

export type RuntimeSummary = {
  state?: string | null;
  running?: boolean | null;
  paused?: boolean | null;
  scheduler_heartbeat_at?: string | null;
  scheduler_heartbeat_age?: number | null;
  scheduler_heartbeat_reason?: string | null;
  scheduler_heartbeat_instance?: string | null;
  scheduler_heartbeat_generation?: number | null;
  scheduler_heartbeat_state?: string | null;
  scheduler_heartbeat_last_error?: string | null;
  worker_state?: boolean | null;
  authorized_watcher_count?: number | null;
  automation_mode?: "event_watcher" | "periodic_reconciliation" | string | null;
  event_watcher_enabled?: boolean | null;
  next_reconciliation_seconds?: number | null;
  reconciliation_interval_seconds?: number | null;
  max_change_detection_delay_seconds?: number | null;
  cleanup_pending?: boolean | null;
  cleanup_error?: string | null;
  last_global_error?: string | null;
};

export type SourceFact = DiscoveredSource & {
  state: SourceState;
  source_id?: string;
  root: string;
  latestScan?: ScanRun;
  nextAction: string;
  detail: string;
};

export type MemorySourcesSnapshot = {
  discovered: DiscoveredSource[];
  authorized: AuthorizedSource[];
  scans: ScanRun[];
  summary: ScanSummary | null;
  runtime: RuntimeSummary | null;
  sources: SourceFact[];
};

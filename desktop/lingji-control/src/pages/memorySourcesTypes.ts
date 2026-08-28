export const SOURCE_STATES = [
  "detected",
  "consent_required",
  "authorized",
  "scanning",
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
  updated_at?: string | null;
  last_error?: string | null;
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

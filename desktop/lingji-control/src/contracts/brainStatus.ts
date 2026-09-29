import type { ResourceAvailability } from "./resourceState";

export type StatusWarning = {
  code?: string;
  stage?: string;
  severity?: "info" | "warning" | "error" | string;
  message?: string;
  action?: string;
  [key: string]: unknown;
};

export type GPUStatus = {
  gpu_id?: string | number | null;
  index?: number | null;
  vendor?: string | null;
  name?: string | null;
  status?: ResourceAvailability | string | null;
  source?: string | null;
  collected_at?: string | null;
  stale?: boolean;
  utilization_percent: number | null;
  temperature_c?: number | null;
  total_vram_bytes?: number | null;
  free_vram_bytes?: number | null;
  used_vram_bytes?: number | null;
  driver_version?: string | null;
  errors?: unknown[];
  [key: string]: unknown;
};

export type TaskSummary = {
  job_id?: string | null;
  task_id?: string | null;
  status?: string | null;
  source_type?: string | null;
  adapter_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
};

export type PipelineHealthSnapshot = {
  name?: string | null;
  consecutive_failures?: number | null;
  total_failures?: number | null;
  degraded?: boolean | null;
  last_error?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  [key: string]: unknown;
};

export type FailureLedgerRecord = {
  failure_key?: string | null;
  source_id?: string | null;
  stage?: string | null;
  reason?: string | null;
  retryable?: boolean | null;
  requires_owner?: boolean | null;
  occurrence_count?: number | null;
  last_seen_at?: string | null;
  [key: string]: unknown;
};

export type FailureLedger = {
  failures?: FailureLedgerRecord[];
  total?: number | null;
  [key: string]: unknown;
};

export type ExtractionQueueStats = {
  queued?: number | null;
  retrying?: number | null;
  running?: number | null;
  completed?: number | null;
  failed?: number | null;
  cancelled?: number | null;
  pending?: number | null;
  [key: string]: unknown;
};

export type StorageSummary = {
  totals?: { bytes?: number | null; files?: number | null; disk_free_bytes?: number | null } | null;
  categories?: Record<string, { bytes?: number | null; files?: number | null; path?: string | null }> | null;
  alerts?: { over_configured_limit?: boolean | null; below_minimum_free?: boolean | null } | null;
  [key: string]: unknown;
};

export type SchedulerJobRow = {
  name?: string | null;
  enabled?: boolean | null;
  interval_seconds?: number | null;
  next_run_at?: string | null;
  last_run_at?: string | null;
  run_count?: number | null;
  paused_reason?: string | null;
  [key: string]: unknown;
};

export type RecentEventRow = {
  event_type?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  created_at?: string | null;
  payload_json?: string | null;
  [key: string]: unknown;
};

export type WatcherStatus = {
  automation_mode?: string | null;
  event_watcher_enabled?: boolean | null;
  authorized_watcher_count?: number | null;
  next_reconciliation_seconds?: number | null;
  last_global_error?: string | null;
  [key: string]: unknown;
};

export type BrainStatusSummary = {
  memory_count: number | null;
  memory_chunk_count: number | null;
  memory_bytes: number | null;
  memory_revision: number | null;
  memory_state: string | null;

  vector_count: number | null;
  vector_state: string | null;
  vector_collection: string | null;
  vector_dimension: number | null;
  vector_rebuild_required: boolean | null;

  embedding_state: string | null;
  chat_model: string | null;
  embed_model: string | null;
  installed_models: number | null;

  gpus: GPUStatus[];
  compute_mode: string | null;
  cuda_version: string | null;

  recent_tasks: TaskSummary[];
  processing_status: string | null;
  system_status: string | null;
  workspace: string | null;

  status_source: string | null;
  status_stale: boolean;
  status_as_of: string | null;
  pipelines: Record<string, PipelineHealthSnapshot>;
  extraction_queue: ExtractionQueueStats | null;
  failure_ledger: FailureLedger | null;
  storage_summary: StorageSummary | null;
  providers: Record<string, unknown>;
  vector_coverage: Record<string, unknown> | null;
  scheduler_jobs: SchedulerJobRow[];
  recent_events: RecentEventRow[];
  watcher_status: WatcherStatus | null;
  warnings: StatusWarning[];
  [key: string]: unknown;
};

const nullableNumber = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const nullableString = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value : null;

const nullableBoolean = (value: unknown): boolean | null =>
  typeof value === "boolean" ? value : null;

export function normalizeBrainStatus(value: unknown): BrainStatusSummary {
  const source = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const rawGpus = Array.isArray(source.gpus) ? source.gpus : [];
  const rawTasks = Array.isArray(source.recent_tasks) ? source.recent_tasks : [];
  const rawWarnings = Array.isArray(source.warnings) ? source.warnings : [];

  return {
    ...source,
    memory_count: nullableNumber(source.memory_count),
    memory_chunk_count: nullableNumber(source.memory_chunk_count),
    memory_bytes: nullableNumber(source.memory_bytes),
    memory_revision: nullableNumber(source.memory_revision),
    memory_state: nullableString(source.memory_state),
    vector_count: nullableNumber(source.vector_count),
    vector_state: nullableString(source.vector_state),
    vector_collection: nullableString(source.vector_collection),
    vector_dimension: nullableNumber(source.vector_dimension),
    vector_rebuild_required: nullableBoolean(source.vector_rebuild_required),
    embedding_state: nullableString(source.embedding_state),
    chat_model: nullableString(source.chat_model),
    embed_model: nullableString(source.embed_model),
    installed_models: nullableNumber(source.installed_models),
    gpus: rawGpus.map((item, index) => {
      const gpu = item && typeof item === "object" ? item as Record<string, unknown> : {};
      return {
        ...gpu,
        gpu_id: gpu.gpu_id as string | number | null | undefined,
        index: nullableNumber(gpu.index) ?? index,
        name: nullableString(gpu.name),
        status: nullableString(gpu.status),
        source: nullableString(gpu.source),
        collected_at: nullableString(gpu.collected_at),
        stale: Boolean(gpu.stale),
        utilization_percent: nullableNumber(gpu.utilization_percent),
        temperature_c: nullableNumber(gpu.temperature_c),
        total_vram_bytes: nullableNumber(gpu.total_vram_bytes),
        free_vram_bytes: nullableNumber(gpu.free_vram_bytes),
        used_vram_bytes: nullableNumber(gpu.used_vram_bytes),
        driver_version: nullableString(gpu.driver_version),
        errors: Array.isArray(gpu.errors) ? gpu.errors : [],
      };
    }),
    compute_mode: nullableString(source.compute_mode),
    cuda_version: nullableString(source.cuda_version),
    recent_tasks: rawTasks.filter((item): item is TaskSummary => Boolean(item && typeof item === "object")),
    processing_status: nullableString(source.processing_status),
    system_status: nullableString(source.system_status),
    workspace: nullableString(source.workspace),
    status_source: nullableString(source.status_source),
    status_stale: Boolean(source.status_stale),
    status_as_of: nullableString(source.status_as_of),
    pipelines: Object.fromEntries(
      Object.entries(
        source.pipelines && typeof source.pipelines === "object"
          ? (source.pipelines as Record<string, unknown>)
          : {},
      ).map(([name, item]) => [
        name,
        item && typeof item === "object" ? (item as PipelineHealthSnapshot) : {},
      ]),
    ),
    extraction_queue:
      source.extraction_queue && typeof source.extraction_queue === "object"
        ? (source.extraction_queue as ExtractionQueueStats)
        : null,
    failure_ledger:
      source.failure_ledger && typeof source.failure_ledger === "object"
        ? (source.failure_ledger as FailureLedger)
        : null,
    storage_summary:
      source.storage_summary && typeof source.storage_summary === "object"
        ? (source.storage_summary as StorageSummary)
        : null,
    providers:
      source.providers && typeof source.providers === "object" ? (source.providers as Record<string, unknown>) : {},
    vector_coverage:
      source.vector_coverage && typeof source.vector_coverage === "object"
        ? (source.vector_coverage as Record<string, unknown>)
        : null,
    scheduler_jobs: Array.isArray(source.scheduler_jobs)
      ? source.scheduler_jobs.filter((item): item is SchedulerJobRow => Boolean(item && typeof item === "object"))
      : [],
    recent_events: Array.isArray(source.recent_events)
      ? source.recent_events.filter((item): item is RecentEventRow => Boolean(item && typeof item === "object"))
      : [],
    watcher_status:
      source.watcher_status && typeof source.watcher_status === "object"
        ? (source.watcher_status as WatcherStatus)
        : null,
    warnings: rawWarnings.filter((item): item is StatusWarning => Boolean(item && typeof item === "object")),
  };
}

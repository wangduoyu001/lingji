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
    warnings: rawWarnings.filter((item): item is StatusWarning => Boolean(item && typeof item === "object")),
  };
}

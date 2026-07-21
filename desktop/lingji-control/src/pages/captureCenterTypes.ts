export type CaptureMode = "normal" | "low_power" | "paused" | string;
export type CaptureJobStatus = "queued" | "running" | "retrying" | "completed" | "failed" | "cancelled" | string;

export type Pagination = { limit: number; offset: number; total: number | null; has_more?: boolean };
export type CaptureResultRefs = { memory_id?: string; source_id?: string; conversation_id?: string; message_id?: string };
export type CaptureJob = {
  job_id: string;
  title?: string | null;
  filename?: string | null;
  source_type?: string | null;
  adapter_name?: string | null;
  status: CaptureJobStatus;
  priority?: number | null;
  attempts?: number | null;
  max_attempts?: number | null;
  progress_current?: number | null;
  progress_total?: number | null;
  progress_message?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  result_summary?: string | null;
  result_refs?: CaptureResultRefs | null;
  privacy?: "private" | "restricted" | string | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
};
export type CaptureJobsResponse = { items: CaptureJob[]; pagination: Pagination; stats?: Record<string, number | null> };
export type CaptureStatusResponse = {
  mode?: CaptureMode | null;
  worker_state?: string | null;
  queued?: number | null;
  running?: number | null;
  retrying?: number | null;
  completed?: number | null;
  failed?: number | null;
  cancelled?: number | null;
  updated_at?: string | null;
};
export type CaptureCapabilitiesResponse = {
  state?: string | null;
  file_modes?: string[];
  media?: { ocr?: boolean; transcription?: boolean; keyframes?: boolean; extract_audio?: boolean; reasons?: Record<string, string> };
};
export type CaptureCommon = { title: string; project_ids: string[]; tags: string[]; privacy: "private" | "restricted"; priority: number; process_later: true; metadata: Record<string, unknown> };
export type CaptureSubmissionResponse = { job_id?: string; duplicate?: boolean; existing_job_id?: string; message?: string };
export type CaptureJobFilters = { status: string; sourceType: string; q: string };
export type CaptureInspectorTarget = CaptureResultRefs;

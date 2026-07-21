import type { LingJiApi } from "../api";
import type {
  CaptureCapabilitiesResponse,
  CaptureCommon,
  CaptureJobsResponse,
  CaptureStatusResponse,
  CaptureSubmissionResponse,
} from "./captureCenterTypes";

export class CaptureCenterApi {
  constructor(private readonly api: LingJiApi) {}

  status(signal?: AbortSignal): Promise<CaptureStatusResponse> {
    return this.api.get("/api/capture/status", { signal });
  }

  capabilities(signal?: AbortSignal): Promise<CaptureCapabilitiesResponse> {
    return this.api.get("/api/capture/capabilities", { signal });
  }

  jobs(query: string, signal?: AbortSignal): Promise<CaptureJobsResponse> {
    return this.api.get(`/api/capture/jobs?${query}`, { signal });
  }

  job(jobId: string, signal?: AbortSignal) {
    return this.api.get(`/api/capture/jobs/${encodeURIComponent(jobId)}`, { signal });
  }

  submitText(payload: CaptureCommon & { text: string; source_type: string }): Promise<CaptureSubmissionResponse> {
    return this.api.post("/api/capture/text", payload);
  }

  submitWeb(payload: CaptureCommon & { url: string; text?: string; author?: string; published_at?: string; platform?: string }): Promise<CaptureSubmissionResponse> {
    return this.api.post("/api/capture/web", payload);
  }

  submitFile(payload: CaptureCommon & { input_path: string; source_type: string; adapter_name?: string }): Promise<CaptureSubmissionResponse> {
    return this.api.post("/api/capture/file", payload);
  }

  submitMedia(payload: CaptureCommon & { input_path: string; allow_ocr: boolean; allow_transcription: boolean; extract_keyframes: boolean; extract_audio: boolean }): Promise<CaptureSubmissionResponse> {
    return this.api.post("/api/capture/media", payload);
  }

  retry(jobId: string): Promise<unknown> {
    return this.api.post(`/api/capture/jobs/${encodeURIComponent(jobId)}/retry`, {});
  }

  cancel(jobId: string): Promise<unknown> {
    return this.api.post(`/api/capture/jobs/${encodeURIComponent(jobId)}/cancel`, {});
  }

  pause(): Promise<unknown> {
    return this.api.post("/api/capture/pause", {});
  }

  resume(): Promise<unknown> {
    return this.api.post("/api/capture/resume", {});
  }
}

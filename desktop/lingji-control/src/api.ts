export type JsonObject = Record<string, unknown>;

const BASE_KEY = "lingji.control.baseUrl";
const TOKEN_KEY = "lingji.control.token";
const DEFAULT_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type RequestOptions = { signal?: AbortSignal; timeoutMs?: number };

export class LingJiApi {
  baseUrl: string;
  token: string;

  constructor() {
    this.baseUrl = localStorage.getItem(BASE_KEY) || "http://127.0.0.1:8766";
    this.token = localStorage.getItem(TOKEN_KEY) || "";
  }

  configure(baseUrl: string, token: string): void {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token.trim();
    localStorage.setItem(BASE_KEY, this.baseUrl);
    localStorage.setItem(TOKEN_KEY, this.token);
  }

  async tryTauriToken(): Promise<void> {
    if (this.token || !("__TAURI_INTERNALS__" in window)) return;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const result = await invoke<{ base_url: string; token: string }>("control_credentials");
      if (result?.token) this.configure(result.base_url || this.baseUrl, result.token);
    } catch { /* Manual setup remains available in browser mode. */ }
  }

  get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { method: "GET" }, options);
  }

  post<T>(path: string, body: JsonObject = {}, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { method: "POST", body: JSON.stringify(body) }, options);
  }

  patch<T>(path: string, body: JsonObject, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, options);
  }

  private async request<T>(path: string, init: RequestInit, options: RequestOptions): Promise<T> {
    const timeout = new AbortController();
    const timer = window.setTimeout(() => timeout.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
    const abort = () => timeout.abort();
    options.signal?.addEventListener("abort", abort, { once: true });
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (this.token) headers.set("X-LingJi-Token", this.token);
    try {
      const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers, signal: timeout.signal });
      const text = await response.text();
      let payload: unknown = null;
      if (text) { try { payload = JSON.parse(text); } catch { payload = text; } }
      if (!response.ok) {
        const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail: unknown }).detail : payload;
        const code = detail && typeof detail === "object" && "code" in detail ? String((detail as { code: unknown }).code) : `HTTP_${response.status}`;
        const message = detail && typeof detail === "object" && "message" in detail ? String((detail as { message: unknown }).message) : String(detail || response.statusText);
        throw new ApiError(response.status, code, message);
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timeout.signal.aborted) throw new ApiError(0, "REQUEST_CANCELLED", options.signal?.aborted ? "Request cancelled" : "Request timed out");
      throw new ApiError(0, "NETWORK_UNAVAILABLE", "Local control service is unavailable");
    } finally {
      window.clearTimeout(timer);
      options.signal?.removeEventListener("abort", abort);
    }
  }
}

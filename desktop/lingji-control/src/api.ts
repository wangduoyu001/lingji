export type JsonObject = Record<string, unknown>;

const DEFAULT_BASE_URL = "http://127.0.0.1:8766";
const DEFAULT_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type RequestOptions = { signal?: AbortSignal; timeoutMs?: number };

export function isTauriDesktopRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export class LingJiApi {
  baseUrl = DEFAULT_BASE_URL;
  token = "";

  configure(baseUrl: string, token: string): void {
    this.baseUrl = (baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
    this.token = token.trim();
  }

  async tryTauriToken(): Promise<boolean> {
    if (!isTauriDesktopRuntime()) return false;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const result = await invoke<{ base_url: string; token: string }>("control_credentials");
      if (!result?.token) {
        throw new ApiError(0, "CREDENTIALS_UNAVAILABLE", "未找到本机控制凭据");
      }
      this.configure(result.base_url || DEFAULT_BASE_URL, result.token);
      return true;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, "DESKTOP_BRIDGE_UNAVAILABLE", "无法读取灵机桌面凭据");
    }
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
      if (text) {
        try { payload = JSON.parse(text); } catch { payload = text; }
      }
      if (!response.ok) {
        const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail: unknown }).detail : payload;
        const code = detail && typeof detail === "object" && "code" in detail ? String((detail as { code: unknown }).code) : `HTTP_${response.status}`;
        const message = detail && typeof detail === "object" && "message" in detail ? String((detail as { message: unknown }).message) : String(detail || response.statusText);
        throw new ApiError(response.status, code, message);
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timeout.signal.aborted) {
        throw new ApiError(0, "REQUEST_CANCELLED", options.signal?.aborted ? "请求已取消" : "本机服务响应超时");
      }
      throw new ApiError(0, "NETWORK_UNAVAILABLE", "本机控制服务不可用");
    } finally {
      window.clearTimeout(timer);
      options.signal?.removeEventListener("abort", abort);
    }
  }
}

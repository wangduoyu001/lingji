export type JsonObject = Record<string, unknown>;

const BASE_KEY = "lingji.control.baseUrl";
const TOKEN_KEY = "lingji.control.token";

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
    } catch {
      // Browser development mode and unconfigured packaged builds fall back to manual setup.
    }
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  post<T>(path: string, body: JsonObject = {}): Promise<T> {
    return this.request<T>(path, { method: "POST", body: JSON.stringify(body) });
  }

  patch<T>(path: string, body: JsonObject): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (this.token) headers.set("X-LingJi-Token", this.token);
    const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    const text = await response.text();
    let payload: unknown = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
    }
    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? String((payload as { detail: unknown }).detail)
          : String(payload || response.statusText);
      throw new Error(detail);
    }
    return payload as T;
  }
}

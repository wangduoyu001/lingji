import type { LingJiApi } from "../api";
import type { SettingsChangePreview, SettingsSnapshot } from "./settingsTypes";

export class SettingsApi {
  constructor(private readonly api: LingJiApi) {}

  snapshot(signal?: AbortSignal): Promise<SettingsSnapshot> {
    return this.api.get<SettingsSnapshot>("/api/settings", signal ? { signal } : undefined);
  }

  preview(values: Record<string, unknown>): Promise<SettingsChangePreview> {
    return this.api.post<SettingsChangePreview>("/api/settings/preview", { values });
  }

  commit(values: Record<string, unknown>, confirmation = ""): Promise<SettingsSnapshot> {
    return this.api.post<SettingsSnapshot>("/api/settings/commit", { values, confirmation });
  }

  reset(keys: string[]): Promise<SettingsSnapshot> {
    return this.api.post<SettingsSnapshot>("/api/settings/reset", { keys });
  }
}

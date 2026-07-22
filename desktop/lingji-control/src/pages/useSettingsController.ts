import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, type LingJiApi } from "../api";
import { SettingsApi } from "./settingsApi";
import type { SettingsChangePreview, SettingsSnapshot } from "./settingsTypes";

function confirmationMessage(preview: SettingsChangePreview): string {
  const changes = preview.high_risk_changes.map((item) => {
    const impacts = Object.values(item.impacts).join("；");
    return `• ${item.label}: ${String(item.from)} → ${String(item.to)}\n  ${impacts}`;
  });
  return [
    "以下高风险设置将被修改：",
    "",
    ...changes,
    "",
    "确认继续保存？",
  ].join("\n");
}

export function useSettingsController(api: LingJiApi, active: boolean) {
  const client = useMemo(() => new SettingsApi(api), [api]);
  const [snapshot, setSnapshot] = useState<SettingsSnapshot | null>(null);
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!active) return;
    try {
      const next = await client.snapshot(signal);
      setSnapshot(next);
      setDraft(next.values);
      setError("");
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "REQUEST_CANCELLED") return;
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, client]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const dirtyValues = useMemo(() => {
    if (!snapshot) return {};
    return Object.fromEntries(
      Object.keys(snapshot.definitions)
        .filter((key) => !Object.is(draft[key], snapshot.values[key]))
        .map((key) => [key, draft[key]]),
    );
  }, [draft, snapshot]);
  const dirtyCount = Object.keys(dirtyValues).length;

  useEffect(() => {
    if (!dirtyCount) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirtyCount]);

  const change = useCallback((key: string, value: unknown) => {
    setMessage("");
    setDraft((current) => ({ ...current, [key]: value }));
  }, []);

  const cancelDraft = useCallback(() => {
    if (!snapshot) return;
    setDraft(snapshot.values);
    setMessage("已取消未保存修改。");
  }, [snapshot]);

  const reload = useCallback(async () => {
    if (dirtyCount && !window.confirm("重新加载会丢弃所有未保存修改，确认继续？")) return;
    await load();
  }, [dirtyCount, load]);

  const save = useCallback(async () => {
    if (!snapshot || !dirtyCount || saving) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const preview = await client.preview(dirtyValues);
      if (preview.errors.length) {
        setError(preview.errors.join("；"));
        return;
      }
      if (!preview.can_commit) {
        setMessage("没有需要保存的有效修改。");
        return;
      }
      let confirmation = "";
      if (preview.requires_confirmation) {
        if (!window.confirm(confirmationMessage(preview))) return;
        confirmation = preview.confirmation_phrase || "";
      }
      const next = await client.commit(preview.normalized_values, confirmation);
      setSnapshot(next);
      setDraft(next.values);
      const warning = preview.warnings.length ? ` 警告：${preview.warnings.join("；")}` : "";
      setMessage(`已保存 ${preview.change_count} 项设置。${warning}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }, [client, dirtyCount, dirtyValues, saving, snapshot]);

  const reset = useCallback(async (keys: string[]) => {
    if (!snapshot || !keys.length || saving) return;
    setSaving(true);
    setError("");
    try {
      const preserved = Object.fromEntries(
        Object.entries(dirtyValues).filter(([key]) => !keys.includes(key)),
      );
      const next = await client.reset(keys);
      setSnapshot(next);
      setDraft({ ...next.values, ...preserved });
      setMessage(`已恢复 ${keys.length} 项系统默认值；其他未保存修改已保留。`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }, [client, dirtyValues, saving, snapshot]);

  return {
    snapshot,
    draft,
    dirtyValues,
    dirtyCount,
    error,
    message,
    saving,
    change,
    save,
    reset,
    reload,
    cancelDraft,
  };
}

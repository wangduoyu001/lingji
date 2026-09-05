import { useCallback, useEffect, useRef, useState } from "react";
import type { LingJiApi } from "../api";
import { decideActionRequired, type ActionRequiredAlert } from "../pages/servicesHealth";

const DISMISS_KEY = "lingji.action-required.dismissed";

function readDismissed(): string[] {
  try {
    const raw = globalThis.localStorage?.getItem(DISMISS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function persistDismissed(items: string[]): void {
  try {
    globalThis.localStorage?.setItem(DISMISS_KEY, JSON.stringify(items.slice(-20)));
  } catch {
    // 删除失败只是意味着提醒可能重复出现；这不是功能失败。
  }
}

export type ActionRequiredState = {
  alert: ActionRequiredAlert | null;
  dismiss: () => void;
  go: () => void;
};

/**
 * 弹窗式提醒：发现"需要主人确认"的事项时主动弹出，而不是等主人翻页面。
 * 同一类提醒关闭后不再重复；事项内容变化时会作为新提醒再次出现。
 */
export function useActionRequiredAlert({
  api,
  active,
  onNavigate,
}: {
  api: LingJiApi;
  active: boolean;
  onNavigate: (page: "memory_sources" | "attention" | "overview") => void;
}): ActionRequiredState {
  const [alert, setAlert] = useState<ActionRequiredAlert | null>(null);
  const dismissedRef = useRef<string[]>(readDismissed());
  const signatureRef = useRef<string>("");

  const evaluate = useCallback(async () => {
    try {
      const [sources, pending] = await Promise.all([
        api.get<Array<{ status?: string; kind?: string; display_name?: string }>>("/api/automatic-memory/discovered"),
        api.get<{ items?: unknown[] }>("/api/work/pending-actions").catch(() => ({ items: [] })),
      ]);
      const projected = sources.map((item) => ({
        state: mapDiscoveredStatus(item.status),
        kind: item.kind,
        display_name: item.display_name,
      }));
      const pendingCount = Array.isArray(pending.items) ? pending.items.length : 0;
      const next = decideActionRequired({ sources: projected, pendingCount, dismissed: dismissedRef.current });
      const signature = next ? `${next.key}:${pendingCount}` : "";
      if (signature !== signatureRef.current) {
        signatureRef.current = signature;
        setAlert(next);
      }
    } catch {
      // 读取失败不弹窗，静默等下一轮。
    }
  }, [api]);

  useEffect(() => {
    if (!active) return;
    void evaluate();
    const timer = window.setInterval(() => void evaluate(), 30_000);
    return () => window.clearInterval(timer);
  }, [active, evaluate]);

  const dismiss = useCallback(() => {
    if (!alert) return;
    dismissedRef.current = [...dismissedRef.current, alert.key];
    persistDismissed(dismissedRef.current);
    signatureRef.current = "";
    setAlert(null);
  }, [alert]);

  const go = useCallback(() => {
    if (!alert) return;
    dismissedRef.current = [...dismissedRef.current, alert.key];
    persistDismissed(dismissedRef.current);
    signatureRef.current = "";
    setAlert(null);
    onNavigate(alert.navigateTo);
  }, [alert, onNavigate]);

  return { alert, dismiss, go };
}

function mapDiscoveredStatus(status: unknown): string {
  const s = String(status ?? "").toLowerCase();
  if (s === "consent_required") return "consent_required";
  if (s === "available") return "detected";
  if (s === "unsupported") return "unsupported";
  return s;
}

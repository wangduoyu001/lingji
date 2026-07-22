import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, LingJiApi, isTauriDesktopRuntime } from "../api";
import type { Row } from "../types";

export type ConnectionState = "booting" | "connected" | "offline" | "unsupported";

function connectionMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "CREDENTIALS_UNAVAILABLE") return "未找到本机控制凭据，请先启动灵机控制服务。";
    if (error.code === "DESKTOP_BRIDGE_UNAVAILABLE") return "桌面桥接不可用，请重新启动灵机桌面应用。";
    if (error.code === "NETWORK_UNAVAILABLE") return "本机控制服务未启动或暂时不可用。";
    return error.message;
  }
  return error instanceof Error ? error.message : String(error);
}

export function useLingJiConnection() {
  const api = useMemo(() => new LingJiApi(), []);
  const [state, setState] = useState<ConnectionState>("booting");
  const [overview, setOverview] = useState<Row | null>(null);
  const [error, setError] = useState("");

  const connect = useCallback(async () => {
    if (!isTauriDesktopRuntime()) {
      setState("unsupported");
      setOverview(null);
      setError("灵机控制中心只作为 Tauri 桌面应用运行，不提供浏览器操作入口。");
      return;
    }
    setState("booting");
    try {
      await api.tryTauriToken();
      const next = await api.get<Row>("/api/overview");
      setOverview(next);
      setState("connected");
      setError("");
    } catch (reason) {
      setOverview(null);
      setState("offline");
      setError(connectionMessage(reason));
    }
  }, [api]);

  useEffect(() => {
    void connect();
  }, [connect]);

  useEffect(() => {
    if (state !== "connected") return;
    const timer = window.setInterval(() => {
      void api.get<Row>("/api/overview")
        .then((next) => {
          setOverview(next);
          setError("");
        })
        .catch((reason) => {
          setState("offline");
          setError(connectionMessage(reason));
        });
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [api, state]);

  return {
    api,
    state,
    connected: state === "connected",
    overview,
    error,
    connect,
  };
}

import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, LingJiApi, isTauriDesktopRuntime } from "../api";
import type { RuntimeStatus } from "../runtimeTypes";
import type { Row } from "../types";

export type ConnectionState = "booting" | "connected" | "offline" | "unsupported";

function connectionMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "CREDENTIALS_UNAVAILABLE") return "灵机核心尚未生成本机控制凭据。";
    if (error.code === "DESKTOP_BRIDGE_UNAVAILABLE") return "桌面桥接不可用，请重新启动灵机桌面应用。";
    if (error.code === "NETWORK_UNAVAILABLE") return "灵机核心未启动或暂时不可用。";
    return error.message;
  }
  return error instanceof Error ? error.message : String(error);
}

function runtimeFailure(status: RuntimeStatus): string {
  if (status.last_error) return status.last_error;
  if (!status.binary_available) return "当前安装包不包含灵机核心 Sidecar。";
  if (status.state === "starting") return "灵机核心仍在启动，请稍后重试。";
  return "灵机核心没有通过本机健康检查。";
}

export function useLingJiConnection() {
  const api = useMemo(() => new LingJiApi(), []);
  const [state, setState] = useState<ConnectionState>("booting");
  const [overview, setOverview] = useState<Row | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [runtimeBusy, setRuntimeBusy] = useState("");
  const [error, setError] = useState("");

  const readOverview = useCallback(async () => {
    await api.tryTauriToken();
    const next = await api.get<Row>("/api/overview");
    setOverview(next);
    setState("connected");
    setError("");
  }, [api]);

  const connect = useCallback(async () => {
    if (!isTauriDesktopRuntime()) {
      setState("unsupported");
      setOverview(null);
      setError("灵机控制中心只作为 Tauri 桌面应用运行，不提供浏览器操作入口。");
      return;
    }
    setState("booting");
    setRuntimeBusy("ensure");
    try {
      const status = await invoke<RuntimeStatus>("runtime_ensure");
      setRuntimeStatus(status);
      if (!status.healthy) throw new Error(runtimeFailure(status));
      await readOverview();
    } catch (reason) {
      setOverview(null);
      setState("offline");
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [readOverview]);

  const refreshRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime()) return null;
    try {
      const status = await invoke<RuntimeStatus>("runtime_status");
      setRuntimeStatus(status);
      return status;
    } catch (reason) {
      setError(connectionMessage(reason));
      return null;
    }
  }, []);

  const stopRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime() || runtimeBusy) return;
    setRuntimeBusy("stop");
    try {
      const status = await invoke<RuntimeStatus>("runtime_stop");
      setRuntimeStatus(status);
      setOverview(null);
      setState("offline");
      setError("灵机核心已由桌面端停止。主人数据没有被删除。");
    } catch (reason) {
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [runtimeBusy]);

  const restartRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime() || runtimeBusy) return;
    setRuntimeBusy("restart");
    setState("booting");
    try {
      const status = await invoke<RuntimeStatus>("runtime_restart");
      setRuntimeStatus(status);
      if (!status.healthy) throw new Error(runtimeFailure(status));
      await readOverview();
    } catch (reason) {
      setOverview(null);
      setState("offline");
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [readOverview, runtimeBusy]);

  useEffect(() => {
    void connect();
  }, [connect]);

  useEffect(() => {
    if (state !== "connected") return;
    const timer = window.setInterval(() => {
      void Promise.all([
        api.get<Row>("/api/overview"),
        invoke<RuntimeStatus>("runtime_status"),
      ])
        .then(([next, runtime]) => {
          setOverview(next);
          setRuntimeStatus(runtime);
          setError("");
          if (!runtime.healthy) setState("offline");
        })
        .catch((reason) => {
          setState("offline");
          setError(connectionMessage(reason));
        });
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [api, state]);

  useEffect(() => {
    if (state === "connected" || state === "unsupported") return;
    const timer = window.setInterval(() => void refreshRuntime(), 5_000);
    return () => window.clearInterval(timer);
  }, [refreshRuntime, state]);

  return {
    api,
    state,
    connected: state === "connected",
    overview,
    runtimeStatus,
    runtimeBusy,
    error,
    connect,
    refreshRuntime,
    stopRuntime,
    restartRuntime,
  };
}

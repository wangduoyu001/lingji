import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, LingJiApi, isTauriDesktopRuntime } from "../api";
import type { RuntimeBootstrapStatus, RuntimeStatus } from "../runtimeTypes";
import type { Row } from "../types";

export type ConnectionState =
  | "booting"
  | "configuration_required"
  | "connected"
  | "offline"
  | "unsupported";

const GUARDED_RUNTIME_COMMANDS = {
  status: "guarded_runtime_status",
  ensure: "guarded_runtime_ensure",
  stop: "guarded_runtime_stop",
  restart: "guarded_runtime_restart",
} as const;

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
  if (status.state === "starting") return "灵机核心仍在启动。";
  return "灵机核心没有通过本机健康检查。";
}

export function useLingJiConnection() {
  const api = useMemo(() => new LingJiApi(), []);
  const [state, setState] = useState<ConnectionState>("booting");
  const [overview, setOverview] = useState<Row | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [bootstrapStatus, setBootstrapStatus] = useState<RuntimeBootstrapStatus | null>(null);
  const [runtimeBusy, setRuntimeBusy] = useState("");
  const [ownerStopped, setOwnerStopped] = useState(false);
  const [error, setError] = useState("");

  const readOverview = useCallback(async () => {
    await api.tryTauriToken();
    const next = await api.get<Row>("/api/overview");
    setOverview(next);
    setState("connected");
    setError("");
  }, [api]);

  const readBootstrap = useCallback(async () => {
    const status = await invoke<RuntimeBootstrapStatus>("runtime_bootstrap_status");
    setBootstrapStatus(status);
    return status;
  }, []);

  const automaticBootstrap = useCallback(async () => {
    const status = await invoke<RuntimeBootstrapStatus>("runtime_autoconfigure");
    setBootstrapStatus(status);
    return status;
  }, []);

  const ensureConnection = useCallback(async (resumeAfterOwnerStop: boolean) => {
    if (!isTauriDesktopRuntime()) {
      setState("unsupported");
      setOverview(null);
      setError("灵机控制中心只作为 Tauri 桌面应用运行，不提供浏览器操作入口。");
      return;
    }
    if (resumeAfterOwnerStop) setOwnerStopped(false);
    setState("booting");
    setRuntimeBusy("ensure");
    try {
      let bootstrap = await readBootstrap();
      if (!bootstrap.configured || bootstrap.c_drive_write_detected) {
        try {
          bootstrap = await automaticBootstrap();
        } catch (automaticReason) {
          setOverview(null);
          setRuntimeStatus(null);
          setState("configuration_required");
          setError(
            `灵机没能自动准备安全的资料目录。${connectionMessage(automaticReason)}`,
          );
          return;
        }
      }
      if (!bootstrap.configured || bootstrap.c_drive_write_detected) {
        setOverview(null);
        setRuntimeStatus(null);
        setState("configuration_required");
        setError(bootstrap.last_error || "灵机没能确定安全的资料目录。");
        return;
      }
      const status = await invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.ensure);
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
  }, [automaticBootstrap, readBootstrap, readOverview]);

  const configureRuntime = useCallback(async (
    baseDataRoot: string,
    workspace: "production" | "acceptance",
  ) => {
    if (!isTauriDesktopRuntime() || runtimeBusy) return;
    setRuntimeBusy("configure");
    setError("");
    try {
      const status = await invoke<RuntimeBootstrapStatus>("runtime_configure", {
        baseDataRoot,
        workspace,
      });
      setBootstrapStatus(status);
      await ensureConnection(false);
    } catch (reason) {
      setState("configuration_required");
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [ensureConnection, runtimeBusy]);

  const connect = useCallback(async () => {
    await ensureConnection(true);
  }, [ensureConnection]);

  const refreshRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime() || bootstrapStatus?.configured === false) return null;
    try {
      const status = await invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.status);
      setRuntimeStatus(status);
      return status;
    } catch (reason) {
      setError(connectionMessage(reason));
      return null;
    }
  }, [bootstrapStatus?.configured]);

  const stopRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime() || runtimeBusy) return;
    setRuntimeBusy("stop");
    setOwnerStopped(true);
    try {
      const status = await invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.stop);
      setRuntimeStatus(status);
      setOverview(null);
      setState("offline");
      setError("灵机核心已由主人停止。后台自动恢复已暂停，数据没有被删除。");
    } catch (reason) {
      setOwnerStopped(false);
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [runtimeBusy]);

  const restartRuntime = useCallback(async () => {
    if (!isTauriDesktopRuntime() || runtimeBusy) return;
    setRuntimeBusy("restart");
    setOwnerStopped(false);
    setState("booting");
    try {
      const status = await invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.restart);
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
    void ensureConnection(false);
  }, [ensureConnection]);

  useEffect(() => {
    if (state !== "connected") return;
    const timer = window.setInterval(() => {
      void Promise.all([
        api.get<Row>("/api/overview"),
        invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.status),
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
    if (state !== "offline" || ownerStopped || runtimeBusy || !isTauriDesktopRuntime()) return;
    const timer = window.setTimeout(() => void ensureConnection(false), 12_000);
    return () => window.clearTimeout(timer);
  }, [ensureConnection, ownerStopped, runtimeBusy, state]);

  useEffect(() => {
    if (["connected", "unsupported", "configuration_required"].includes(state)) return;
    const timer = window.setInterval(() => void refreshRuntime(), 5_000);
    return () => window.clearInterval(timer);
  }, [refreshRuntime, state]);

  return {
    api,
    state,
    connected: state === "connected",
    overview,
    runtimeStatus,
    bootstrapStatus,
    runtimeBusy,
    ownerStopped,
    autoRecoveryActive: state === "offline" && !ownerStopped,
    error,
    connect,
    configureRuntime,
    refreshRuntime,
    stopRuntime,
    restartRuntime,
  };
}

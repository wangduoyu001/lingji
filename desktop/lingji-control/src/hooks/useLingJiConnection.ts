import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, LingJiApi, isTauriDesktopRuntime } from "../api";
import type {
  AutopilotStatus,
  RuntimeBindingVerification,
  RuntimeBootstrapStatus,
  RuntimeStatus,
} from "../runtimeTypes";
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

const INITIAL_AUTOPILOT: AutopilotStatus = {
  state: "idle",
  current_action: "等待核心连接",
  completed_actions: [],
  failed_actions: [],
  last_run_at: null,
};

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
  const autopilotRunning = useRef(false);
  const [state, setState] = useState<ConnectionState>("booting");
  const [overview, setOverview] = useState<Row | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [bootstrapStatus, setBootstrapStatus] = useState<RuntimeBootstrapStatus | null>(null);
  const [bindingVerification, setBindingVerification] = useState<RuntimeBindingVerification | null>(null);
  const [autopilotStatus, setAutopilotStatus] = useState<AutopilotStatus>(INITIAL_AUTOPILOT);
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

  const readBindingVerification = useCallback(async () => {
    const verification = await invoke<RuntimeBindingVerification>("runtime_binding_verification");
    setBindingVerification(verification);
    return verification;
  }, []);

  const runSafeAutopilot = useCallback(async () => {
    if (autopilotRunning.current) return;
    autopilotRunning.current = true;
    setAutopilotStatus({
      state: "running",
      current_action: "自动扫描本机 AI、模型与运行环境",
      completed_actions: [],
      failed_actions: [],
      last_run_at: null,
    });

    const actions = [
      {
        label: "扫描 AI 软件与历史目录元数据",
        run: () => api.post("/api/assistant-hub/scan"),
      },
      {
        label: "刷新本机模型状态",
        run: () => api.post("/api/models/refresh"),
      },
      {
        label: "刷新硬件与运行能力",
        run: () => api.post("/api/hardware/refresh"),
      },
    ];
    const results = await Promise.allSettled(actions.map((action) => action.run()));
    const completed = actions
      .filter((_, index) => results[index].status === "fulfilled")
      .map((action) => action.label);
    const failed = actions
      .filter((_, index) => results[index].status === "rejected")
      .map((action) => action.label);
    setAutopilotStatus({
      state: failed.length ? "degraded" : "completed",
      current_action: failed.length
        ? "安全自动任务已完成，部分状态等待后台重试"
        : "安全自动任务已完成，等待需要主人授权的操作",
      completed_actions: completed,
      failed_actions: failed,
      last_run_at: new Date().toISOString(),
    });
    autopilotRunning.current = false;
  }, [api]);

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
        if (!bootstrap.startup_contract_detected) {
          try {
            bootstrap = await invoke<RuntimeBootstrapStatus>("runtime_auto_configure");
            setBootstrapStatus(bootstrap);
          } catch {
            // The manual directory menu is the final fallback when no writable
            // non-C drive can be selected automatically.
          }
        }
      }
      if (!bootstrap.configured || bootstrap.c_drive_write_detected) {
        setOverview(null);
        setRuntimeStatus(null);
        setBindingVerification(null);
        setState("configuration_required");
        setError(bootstrap.last_error || "灵机没有找到可写的非 C 盘，请选择一次数据目录。");
        return;
      }
      const status = await invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.ensure);
      setRuntimeStatus(status);
      if (!status.healthy) throw new Error(runtimeFailure(status));
      const verification = await readBindingVerification();
      if (!verification.verified) {
        throw new Error(verification.error || "Runtime DataRoot绑定未通过验证。");
      }
      await readOverview();
      void runSafeAutopilot();
    } catch (reason) {
      setOverview(null);
      setState("offline");
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [readBindingVerification, readBootstrap, readOverview, runSafeAutopilot]);

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
      if (status.healthy) {
        const verification = await readBindingVerification();
        if (!verification.verified) {
          setState("offline");
          setError(verification.error || "Runtime DataRoot绑定漂移，已停止自动接管。");
        }
      }
      return status;
    } catch (reason) {
      setError(connectionMessage(reason));
      return null;
    }
  }, [bootstrapStatus?.configured, readBindingVerification]);

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
      const verification = await readBindingVerification();
      if (!verification.verified) {
        throw new Error(verification.error || "Runtime DataRoot绑定未通过验证。");
      }
      await readOverview();
      void runSafeAutopilot();
    } catch (reason) {
      setOverview(null);
      setState("offline");
      setError(connectionMessage(reason));
    } finally {
      setRuntimeBusy("");
    }
  }, [readBindingVerification, readOverview, runSafeAutopilot, runtimeBusy]);

  useEffect(() => {
    void ensureConnection(false);
  }, [ensureConnection]);

  useEffect(() => {
    if (state !== "connected") return;
    const timer = window.setInterval(() => {
      void Promise.all([
        api.get<Row>("/api/overview"),
        invoke<RuntimeStatus>(GUARDED_RUNTIME_COMMANDS.status),
        invoke<RuntimeBindingVerification>("runtime_binding_verification"),
      ])
        .then(([next, runtime, verification]) => {
          setOverview(next);
          setRuntimeStatus(runtime);
          setBindingVerification(verification);
          if (!verification.verified) {
            setState("offline");
            setError(verification.error || "Runtime DataRoot绑定漂移，已拒绝继续连接。");
            return;
          }
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
    bindingVerification,
    autopilotStatus,
    runtimeBusy,
    ownerStopped,
    autoRecoveryActive: state === "offline" && !ownerStopped,
    error,
    connect,
    configureRuntime,
    refreshRuntime,
    runSafeAutopilot,
    stopRuntime,
    restartRuntime,
  };
}

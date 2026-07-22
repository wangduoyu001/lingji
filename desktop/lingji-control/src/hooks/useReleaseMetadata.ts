import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";
import { isTauriDesktopRuntime } from "../api";
import type { RuntimeStatus } from "../runtimeTypes";

export type ReleaseMetadata = {
  product_name: string;
  version: string;
  commit: string;
  build_time_utc: string;
  channel: string;
  target: string;
  installer_format: string;
  signed: boolean;
};

export function useReleaseMetadata() {
  const [metadata, setMetadata] = useState<ReleaseMetadata | null>(null);

  useEffect(() => {
    if (!isTauriDesktopRuntime()) return;
    void invoke<ReleaseMetadata>("release_metadata")
      .then(setMetadata)
      .catch(() => setMetadata(null));
  }, []);

  const copyDiagnostics = useCallback(async (
    connectionState: string,
    connected: boolean,
    runtimeStatus: RuntimeStatus | null,
  ) => {
    const lines = [
      `product=${metadata?.product_name ?? "LingJi"}`,
      `version=${metadata?.version ?? "unknown"}`,
      `commit=${metadata?.commit ?? "unknown"}`,
      `build_time_utc=${metadata?.build_time_utc ?? "unknown"}`,
      `channel=${metadata?.channel ?? "unknown"}`,
      `target=${metadata?.target ?? "unknown"}`,
      `installer_format=${metadata?.installer_format ?? "unknown"}`,
      `signed=${metadata?.signed === true ? "true" : "false"}`,
      `connection_state=${connectionState}`,
      `control_service=${connected ? "connected" : "disconnected"}`,
      `runtime_state=${runtimeStatus?.state ?? "unknown"}`,
      `runtime_healthy=${runtimeStatus?.healthy === true ? "true" : "false"}`,
      `runtime_managed=${runtimeStatus?.managed === true ? "true" : "false"}`,
      `runtime_pid=${runtimeStatus?.pid ?? "none"}`,
      `runtime_restart_count=${runtimeStatus?.restart_count ?? 0}`,
      `runtime_last_exit_code=${runtimeStatus?.last_exit_code ?? "none"}`,
      `runtime_binary_available=${runtimeStatus?.binary_available === true ? "true" : "false"}`,
      `runtime_data_root=${runtimeStatus?.data_root_display ?? "unknown"}`,
      `runtime_log=${runtimeStatus?.log_path_display ?? "unknown"}`,
      `platform=${navigator.platform || "unknown"}`,
      `user_agent=${navigator.userAgent}`,
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  }, [metadata]);

  return { metadata, copyDiagnostics };
}

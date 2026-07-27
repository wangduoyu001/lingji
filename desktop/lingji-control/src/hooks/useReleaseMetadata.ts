import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";
import { isTauriDesktopRuntime } from "../api";
import type { RuntimeBootstrapStatus, RuntimeStatus } from "../runtimeTypes";
import type { Row } from "../types";

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

const record = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" ? value as Record<string, unknown> : {};

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
    bootstrapStatus: RuntimeBootstrapStatus | null,
    overview: Row | null,
  ) => {
    const root = record(overview);
    const health = record(root.health);
    const memoryRuntime = record(root.memory_runtime);
    const memory = record(memoryRuntime.memory ?? root.memory_stats);
    const vector = record(memoryRuntime.vector ?? root.vector_status);
    const embedding = record(memoryRuntime.embedding ?? root.embedding_status);
    const queue = record(record(root.queue).stats);
    const storage = record(record(root.storage).totals);
    const scheduler = Array.isArray(root.scheduler) ? root.scheduler : [];

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
      `control_api_port=${runtimeStatus?.port ?? 8766}`,
      `runtime_state=${runtimeStatus?.state ?? "unknown"}`,
      `runtime_healthy=${runtimeStatus?.healthy === true ? "true" : "false"}`,
      `runtime_managed=${runtimeStatus?.managed === true ? "true" : "false"}`,
      `runtime_pid=${runtimeStatus?.pid ?? "none"}`,
      `runtime_restart_count=${runtimeStatus?.restart_count ?? 0}`,
      `runtime_last_exit_code=${runtimeStatus?.last_exit_code ?? "none"}`,
      `runtime_binary_available=${runtimeStatus?.binary_available === true ? "true" : "false"}`,
      `bootstrap_configured=${bootstrapStatus?.configured === true ? "true" : "false"}`,
      `bootstrap_source=${bootstrapStatus?.source ?? "unknown"}`,
      `inherited_runtime_environment_ignored=${bootstrapStatus?.inherited_environment_ignored === true ? "true" : "false"}`,
      `workspace=${bootstrapStatus?.active_workspace ?? memoryRuntime.workspace ?? "unknown"}`,
      `runtime_data_root=${bootstrapStatus?.data_root_display ?? runtimeStatus?.data_root_display ?? "unknown"}`,
      `runtime_log=${runtimeStatus?.log_path_display ?? "unknown"}`,
      `c_drive_write_detected=${bootstrapStatus?.c_drive_write_detected === true ? "true" : "false"}`,
      `system_health=${health.status ?? "unknown"}`,
      `system_health_errors=${health.error_count ?? "unknown"}`,
      `system_health_warnings=${health.warning_count ?? "unknown"}`,
      `memory_state=${memory.state ?? "unknown"}`,
      `memory_documents=${memory.documents ?? "unknown"}`,
      `memory_revision=${memory.revision ?? "unknown"}`,
      `vector_state=${vector.state ?? "unknown"}`,
      `vector_collection=${vector.collection ?? "unknown"}`,
      `vector_count=${vector.vectors ?? "unknown"}`,
      `vector_dimension=${vector.dimension ?? "unknown"}`,
      `vector_rebuild_required=${vector.rebuild_required === true ? "true" : "false"}`,
      `embedding_state=${embedding.state ?? "unknown"}`,
      `embedding_configured_model=${embedding.configured_model ?? "unknown"}`,
      `embedding_active_model=${embedding.active_model ?? "unknown"}`,
      `tasks_pending=${queue.pending ?? "unknown"}`,
      `tasks_running=${queue.running ?? "unknown"}`,
      `tasks_failed=${queue.failed ?? "unknown"}`,
      `scheduler_jobs=${scheduler.length}`,
      `storage_free_bytes=${storage.disk_free_bytes ?? "unknown"}`,
      `platform=${navigator.platform || "unknown"}`,
      `user_agent=${navigator.userAgent}`,
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  }, [metadata]);

  return { metadata, copyDiagnostics };
}

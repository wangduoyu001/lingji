import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { isTauriDesktopRuntime } from "../api";

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

  const copyDiagnostics = useCallback(async (connectionState: string, connected: boolean) => {
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
      `platform=${navigator.platform || "unknown"}`,
      `user_agent=${navigator.userAgent}`,
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  }, [metadata]);

  return { metadata, copyDiagnostics };
}

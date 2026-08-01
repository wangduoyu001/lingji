export type RuntimeManagerState =
  | "stopped"
  | "starting"
  | "healthy"
  | "unhealthy"
  | "external"
  | "failed"
  | string;

export type RuntimeBootstrapStatus = {
  configured: boolean;
  active_workspace: "production" | "acceptance" | null;
  base_data_root_display: string | null;
  data_root_display: string | null;
  config_path_display: string;
  source: string;
  binding_id: string | null;
  binding_locked: boolean;
  c_drive_write_detected: boolean;
  inherited_environment_ignored: boolean;
  startup_contract_detected: boolean;
  last_error: string | null;
};

export type RuntimeBindingVerification = {
  verified: boolean;
  expected_data_root: string | null;
  actual_data_root: string | null;
  expected_workspace: string | null;
  actual_workspace: string | null;
  source: string;
  binding_id: string | null;
  binding_locked: boolean;
  error: string | null;
};

export type RuntimeStatus = {
  state: RuntimeManagerState;
  healthy: boolean;
  managed: boolean;
  pid: number | null;
  started_at_ms: number | null;
  restart_count: number;
  last_exit_code: number | null;
  last_error: string | null;
  binary_available: boolean;
  data_root_display: string;
  log_path_display: string;
  host: string;
  port: number;
};

export type AutopilotStatus = {
  state: "idle" | "running" | "waiting_authorization" | "completed" | "degraded";
  current_action: string;
  completed_actions: string[];
  failed_actions: string[];
  last_run_at: string | null;
};

export const runtimeStateLabel = (status: RuntimeStatus | null): string => {
  if (!status) return "正在读取核心状态";
  if (status.healthy && status.managed) return "灵机核心运行中";
  if (status.healthy && !status.managed) return "发现未托管核心，等待身份核验";
  const labels: Record<string, string> = {
    stopped: "灵机核心已停止",
    starting: "灵机核心启动中",
    unhealthy: "灵机核心未就绪",
    failed: "灵机核心启动失败",
    external: "发现外部核心，已拒绝自动接管",
  };
  return labels[status.state] ?? status.state;
};

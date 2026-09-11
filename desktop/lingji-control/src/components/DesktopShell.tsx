import { useCallback, useState, type ReactNode } from "react";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import { PRIMARY_NAVIGATION } from "../navigation";
import type { ReleaseMetadata } from "../hooks/useReleaseMetadata";
import type { ConnectionState } from "../hooks/useLingJiConnection";
import {
  type RuntimeBootstrapStatus,
  type RuntimeStatus,
} from "../runtimeTypes";
import type { NavigationItem, PageId } from "../types";
import NavIcon from "./NavIcon";

type Props = {
  page: PageId;
  current: NavigationItem;
  connected: boolean;
  api: LingJiApi | null;
  connectionState: ConnectionState;
  releaseMetadata: ReleaseMetadata | null;
  runtimeStatus: RuntimeStatus | null;
  bootstrapStatus: RuntimeBootstrapStatus | null;
  runtimeBusy: string;
  ownerStopped: boolean;
  autoRecoveryActive: boolean;
  onNavigate: (page: PageId) => void;
  onRetry: () => void;
  onStopRuntime: () => void;
  onRestartRuntime: () => void;
  onCopyDiagnostics: () => Promise<void>;
  children: ReactNode;
};

export default function DesktopShell({
  page,
  current,
  connected,
  api,
  connectionState,
  releaseMetadata,
  runtimeStatus,
  bootstrapStatus,
  runtimeBusy,
  ownerStopped,
  autoRecoveryActive,
  onNavigate,
  onRetry,
  onStopRuntime,
  onRestartRuntime,
  onCopyDiagnostics,
  children,
}: Props) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const shortCommit = releaseMetadata?.commit && releaseMetadata.commit !== "development"
    ? releaseMetadata.commit.slice(0, 8)
    : "dev";
  const runtimeHealthy = runtimeStatus?.healthy === true;
  const managedRuntime = runtimeHealthy && runtimeStatus?.managed === true;
  const externalRuntime = runtimeHealthy && runtimeStatus?.managed === false;
  const runtimeAvailable = runtimeStatus?.binary_available !== false;
  const runtimeConfigured = bootstrapStatus?.configured === true && !bootstrapStatus.c_drive_write_detected;
  const copyDiagnostics = async () => {
    try {
      await onCopyDiagnostics();
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2200);
  };

  const shellStateLabel = runtimeHealthy ? "自动记忆运行中" : connectionState === "configuration_required" ? "等待首次设置" : "正在恢复";

  return (
    <div className="desktop-frame">
      <aside className="desktop-sidebar" aria-label="灵机主导航">
        <div className="desktop-brand">
          <div className="desktop-brand-mark">灵</div>
          <div className="desktop-brand-copy">
            <strong>灵机</strong>
            <span>你的第二大脑</span>
          </div>
        </div>

        <nav className="desktop-nav desktop-nav-primary">
          <div className="desktop-nav-items">
            {PRIMARY_NAVIGATION.map((item) => (
              <button
                key={item.id}
                className={page === item.id ? "desktop-nav-item active" : "desktop-nav-item"}
                onClick={() => onNavigate(item.id)}
                title={item.hint}
                aria-label={item.label}
                aria-current={page === item.id ? "page" : undefined}
              >
                <span className="desktop-nav-icon"><NavIcon name={item.icon} /></span>
                <span className="desktop-nav-copy">
                  <strong>{item.label}</strong>
                </span>
              </button>
            ))}
          </div>
        </nav>
        {connected && api != null && <SidebarModelSwitch api={api} onNavigate={onNavigate} page={page} />}

        <details className="desktop-advanced-disclosure">
          <summary className="desktop-diagnostics-link">高级诊断</summary>
          <div className="desktop-advanced-disclosure-body">
            <p>日常不需要进入这里。状态异常或需要核查时，再打开详细页面。</p>
            <button className="desktop-advanced-open" onClick={() => onNavigate("diagnostics")}>打开高级诊断</button>
          </div>
        </details>

        <div className="desktop-sidebar-status">
          <div className="desktop-status-line">
            <span className={runtimeHealthy ? "status-dot online" : "status-dot"} />
            <div>
              <strong>{shellStateLabel}</strong>
              <small>
                {runtimeStatus
                  ? runtimeHealthy ? "可以继续使用" : "请按下方提示处理"
                  : connectionState === "configuration_required"
                    ? "核心尚未启动"
                    : "正在读取本机核心"}
              </small>
            </div>
          </div>

          {bootstrapStatus?.c_drive_write_detected && (
            <small className="desktop-runtime-error">检测到 C 盘运行数据路径，核心已阻止启动。</small>
          )}
          {autoRecoveryActive && <small className="desktop-runtime-warning">连接中断，灵机会自动恢复，无需手动操作。</small>}
          {ownerStopped && <small className="desktop-runtime-warning">主人已停止核心，自动恢复暂时暂停。</small>}
          {!runtimeAvailable && runtimeConfigured && connectionState !== "unsupported" && (
            <small className="desktop-runtime-warning">当前安装包未包含灵机核心，请检查安装或联系支持。</small>
          )}

          {connectionState !== "unsupported" && connectionState !== "configuration_required" && (
            <details className="desktop-runtime-tools" open={ownerStopped}>
              <summary>{runtimeHealthy ? "运行详情" : ownerStopped ? "恢复与诊断" : "故障工具"}</summary>
              <div className="desktop-runtime-technical">
                {bootstrapStatus?.active_workspace && <small className="desktop-runtime-path">工作区：{bootstrapStatus.active_workspace} · {bootstrapStatus.data_root_display || "数据根未知"}</small>}
                {runtimeStatus?.last_error && <small className="desktop-runtime-error">内部错误：{runtimeStatus.last_error}</small>}
                <div className="desktop-release-line">
                  <span>版本 v{releaseMetadata?.version ?? "0.1.0"}</span>
                  <span>渠道 {releaseMetadata?.channel ?? "development"}</span>
                  <span>提交 {shortCommit}</span>
                </div>
                <small>连接方式：{externalRuntime ? "已连接到本机服务（外部进程）" : managedRuntime ? "灵机核心正在运行" : "核心状态已连接"}</small>
              </div>
              <div className="desktop-sidebar-actions">
                {!runtimeHealthy && (
                  <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRetry}>
                    {runtimeBusy === "ensure" ? "恢复中…" : ownerStopped ? "恢复运行" : "立即重试"}
                  </button>
                )}
                {managedRuntime && (
                  <>
                    <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRestartRuntime}>
                      {runtimeBusy === "restart" ? "重启中…" : "重启核心"}
                    </button>
                    <button className="desktop-stop-button" disabled={Boolean(runtimeBusy)} onClick={onStopRuntime}>
                      {runtimeBusy === "stop" ? "停止中…" : "停止核心"}
                    </button>
                  </>
                )}
                {externalRuntime && !connected && (
                  <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRetry}>重新连接</button>
                )}
                <button className="desktop-diagnostics-button" onClick={() => void copyDiagnostics()}>
                  {copyState === "copied" ? "诊断信息已复制" : copyState === "failed" ? "复制失败" : "复制诊断信息"}
                </button>
              </div>
            </details>
          )}
        </div>
      </aside>

      <main className="desktop-main">
        <header className="desktop-toolbar">
          <div className="desktop-toolbar-copy">
            <h1>{current.label}</h1>
            <p>{current.group === "observe" ? "灵机自动整理你的记录，这里只展示当前结果。" : current.hint}</p>
          </div>
          <div className={connected ? "desktop-connection-badge connected" : "desktop-connection-badge"}>
            <span className={connected ? "status-dot online" : "status-dot"} />
            <span>
              {connected
                ? "运行中"
                : connectionState === "booting"
                  ? "启动中"
                  : connectionState === "configuration_required"
                    ? "需要配置"
                    : ownerStopped
                      ? "已暂停"
                      : "自动恢复中"}
            </span>
          </div>
        </header>
        <div className="desktop-content">{children}</div>
      </main>
    </div>
  );
}


type KnowledgeBrief = {
  provider?: "local" | "zhipu";
  zhipu_key_set?: boolean;
  distill_model?: string;
  models?: Array<{ name: string; size_bytes: number; active: boolean }>;
  stats?: { ready: number; total: number; pending: number };
};

function SidebarModelSwitch({ api, onNavigate, page }: { api: LingJiApi; onNavigate: (page: PageId) => void; page: PageId }) {
  const resource = usePollingResource<KnowledgeBrief>({
    fetcher: useCallback(
      (signal: AbortSignal) => api.get("/api/observability/knowledge?limit=1", { signal }),
      [api],
    ),
    enabled: true,
    intervalMs: 30_000,
    staleAfterMs: 90_000,
  });
  const [busy, setBusy] = useState(false);
  const provider = resource.data?.provider || "local";
  const keySet = resource.data?.zhipu_key_set === true;
  const distillModel = (resource.data?.distill_model || "").trim();
  const localModel = distillModel || ((resource.data?.models ?? []).find((model) => model.active)?.name ?? "自动");

  const update = async (payload: Record<string, string>) => {
    setBusy(true);
    try {
      await api.post("/api/observability/knowledge/provider", payload);
      await resource.refresh();
    } catch {
      // 失败保持原状。
    } finally {
      setBusy(false);
    }
  };

  const stats = resource.data?.stats;
  const label = provider === "zhipu"
    ? (keySet ? "GLM-4-Flash（云端）" : "GLM-4-Flash（待配 Key）")
    : localModel.split(":")[0];

  return (
    <div className="sidebar-model-switch" aria-label="提炼模型快切">
      <button
        className={`sidebar-model-button${page === "memory_library" ? " active" : ""}`}
        onClick={() => onNavigate("memory_library")}
        title="点开记忆库可看提炼进度与详细设置"
      >
        <span className="pill neutral">{provider === "zhipu" ? "云端" : "本机"}</span>
        <strong>提炼：{label}</strong>
        {stats && stats.pending > 0 ? <small>待提炼 {stats.pending}</small> : <small>提炼正常</small>}
      </button>
      {page === "memory_library" && (
        <div className="sidebar-model-detail">
          <select
            aria-label="提炼服务"
            disabled={busy}
            value={provider}
            onChange={(event) => void update({ provider: event.target.value })}
          >
            <option value="local">本机模型</option>
            <option value="zhipu">云端 GLM-4-Flash</option>
          </select>
          {provider === "local" && (
            <select
              aria-label="本机提炼模型"
              disabled={busy}
              value={resource.data?.distill_model || ""}
              onChange={(event) => {
                const model = event.target.value;
                setBusy(true);
                api
                  .post("/api/observability/knowledge/model", { model })
                  .then(() => resource.refresh())
                  .catch(() => undefined)
                  .finally(() => setBusy(false));
              }}
            >
              <option value="">自动（最小模型）</option>
              {(resource.data?.models ?? []).map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name.split(":")[0]}
                </option>
              ))}
            </select>
          )}
        </div>
      )}
    </div>
  );
}

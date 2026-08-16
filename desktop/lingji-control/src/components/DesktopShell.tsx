import { useState, type ReactNode } from "react";
import type { LingJiApi } from "../api";
import { NAVIGATION_GROUPS, PRIMARY_NAVIGATION } from "../navigation";
import type { ReleaseMetadata } from "../hooks/useReleaseMetadata";
import type { ConnectionState } from "../hooks/useLingJiConnection";
import { runtimeStateLabel, type RuntimeBootstrapStatus, type RuntimeStatus } from "../runtimeTypes";
import type { NavigationItem, PageId } from "../types";
import GlobalOwnerCommand from "./GlobalOwnerCommand";
import NavIcon from "./NavIcon";

type Props = {
  api: LingJiApi;
  page: PageId;
  current: NavigationItem;
  connected: boolean;
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
  api,
  page,
  current,
  connected,
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
  const advancedPage = current.group === "advanced" || page === "diagnostics";

  const copyDiagnostics = async () => {
    try {
      await onCopyDiagnostics();
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2200);
  };

  const ownerState = connectionState === "configuration_required"
    ? { title: "需要设置资料位置", detail: "灵机还没有开始工作", tone: "warning" }
    : ownerStopped
      ? { title: "灵机已暂停", detail: "后台观察和处理已暂停", tone: "paused" }
      : connected && runtimeHealthy
        ? { title: "灵机正在工作", detail: "会继续观察已授权环境", tone: "ok" }
        : autoRecoveryActive || connectionState === "booting"
          ? { title: "灵机正在恢复", detail: "无需手动刷新", tone: "working" }
          : { title: "灵机暂时不可用", detail: "正在等待本机核心恢复", tone: "warning" };

  return (
    <div className="desktop-frame workbench-shell-v4">
      <aside className="desktop-sidebar v4-sidebar" aria-label="灵机主导航">
        <div className="desktop-brand v4-brand">
          <div className="desktop-brand-mark">灵</div>
          <div className="desktop-brand-copy">
            <strong>灵机</strong>
            <span>第二永久记忆大脑</span>
          </div>
        </div>

        <nav className="desktop-nav desktop-nav-primary v4-primary-nav">
          <div className="desktop-nav-items">
            {PRIMARY_NAVIGATION.map((item) => (
              <button
                key={item.id}
                className={page === item.id ? "desktop-nav-item active" : "desktop-nav-item"}
                onClick={() => onNavigate(item.id)}
                title={item.hint}
                aria-current={page === item.id ? "page" : undefined}
              >
                <span className="desktop-nav-icon"><NavIcon name={item.icon} /></span>
                <span className="desktop-nav-copy"><strong>{item.label}</strong><small>{item.hint}</small></span>
              </button>
            ))}
          </div>
        </nav>

        <div className="v4-sidebar-spacer" />

        <div className={`v4-owner-runtime ${ownerState.tone}`}>
          <div className="v4-owner-runtime-summary">
            <span className={`v4-runtime-dot ${ownerState.tone}`} />
            <div><strong>{ownerState.title}</strong><small>{ownerState.detail}</small></div>
          </div>

          {(bootstrapStatus?.c_drive_write_detected || runtimeStatus?.last_error) && (
            <div className="v4-runtime-owner-warning">
              {bootstrapStatus?.c_drive_write_detected ? "检测到不允许的运行数据位置，核心已阻止启动。" : "最近一次核心恢复没有成功。"}
            </div>
          )}

          <details className="desktop-runtime-tools v4-runtime-details" open={ownerStopped}>
            <summary>运行与诊断详情</summary>
            <div className="v4-runtime-facts">
              <span>状态 <strong>{connectionState === "configuration_required" ? "等待配置" : runtimeStateLabel(runtimeStatus)}</strong></span>
              <span>核心 <strong>{runtimeStatus ? `${runtimeStatus.host}:${runtimeStatus.port}` : "读取中"}</strong></span>
              {managedRuntime && <span>进程 <strong>PID {runtimeStatus?.pid ?? "未知"}</strong></span>}
              {externalRuntime && <span>进程 <strong>外部核心</strong></span>}
              {bootstrapStatus?.active_workspace && <span>工作区 <strong>{bootstrapStatus.active_workspace}</strong></span>}
              {bootstrapStatus?.data_root_display && <span>资料位置 <strong>{bootstrapStatus.data_root_display}</strong></span>}
              <span>版本 <strong>v{releaseMetadata?.version ?? "0.1.0"} · {shortCommit}</strong></span>
            </div>

            {!runtimeAvailable && runtimeConfigured && connectionState !== "unsupported" && (
              <small className="desktop-runtime-warning">当前安装包没有内置核心，只能连接手动启动的本机服务。</small>
            )}
            {autoRecoveryActive && <small className="desktop-runtime-warning">连接中断后正在自动恢复。</small>}
            {runtimeStatus?.last_error && <small className="desktop-runtime-error">{runtimeStatus.last_error}</small>}

            <div className="desktop-sidebar-actions">
              {!runtimeHealthy && connectionState !== "configuration_required" && (
                <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRetry}>
                  {runtimeBusy === "ensure" ? "恢复中…" : ownerStopped ? "恢复运行" : "重新连接"}
                </button>
              )}
              {managedRuntime && (
                <>
                  <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRestartRuntime}>{runtimeBusy === "restart" ? "重启中…" : "重启核心"}</button>
                  <button className="desktop-stop-button" disabled={Boolean(runtimeBusy)} onClick={onStopRuntime}>{runtimeBusy === "stop" ? "停止中…" : "暂停核心"}</button>
                </>
              )}
              {externalRuntime && !connected && <button className="desktop-retry-button" disabled={Boolean(runtimeBusy)} onClick={onRetry}>重新连接</button>}
              <button className="desktop-diagnostics-button" onClick={() => void copyDiagnostics()}>{copyState === "copied" ? "诊断信息已复制" : copyState === "failed" ? "复制失败" : "复制诊断信息"}</button>
            </div>
          </details>
        </div>
      </aside>

      <main className="desktop-main v4-main">
        <header className="desktop-toolbar v4-toolbar">
          <div className="v4-toolbar-topline">
            <div className="desktop-toolbar-copy">
              <div className="desktop-breadcrumb">
                {advancedPage ? `灵机 / ${NAVIGATION_GROUPS.find((group) => group.id === "advanced")?.label ?? "高级"}` : "灵机 / 日常"}
                {current.group === "advanced" && <button className="toolbar-back-button" onClick={() => onNavigate("diagnostics")}>返回高级</button>}
              </div>
              <h1>{current.label}</h1>
              <p>{current.hint}</p>
            </div>
            <div className={`v4-connection-chip ${connected ? "connected" : ""}`}><span className={`v4-runtime-dot ${runtimeHealthy ? "ok" : "warning"}`} /><span>{connected ? "在线" : connectionState === "booting" ? "启动中" : ownerStopped ? "已暂停" : "恢复中"}</span></div>
          </div>
          <GlobalOwnerCommand api={api} connected={connected} onNavigate={onNavigate} />
        </header>
        <div className="desktop-content v4-content">{children}</div>
      </main>
    </div>
  );
}

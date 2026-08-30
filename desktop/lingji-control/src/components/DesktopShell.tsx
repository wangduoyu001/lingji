import { useState, type ReactNode } from "react";
import { NAVIGATION_GROUPS, PRIMARY_NAVIGATION } from "../navigation";
import type { ReleaseMetadata } from "../hooks/useReleaseMetadata";
import type { ConnectionState } from "../hooks/useLingJiConnection";
import {
  runtimeStateLabel,
  type RuntimeBootstrapStatus,
  type RuntimeStatus,
} from "../runtimeTypes";
import type { NavigationItem, PageId } from "../types";
import NavIcon from "./NavIcon";

type Props = {
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
  const advancedPage = current.group === "advanced" && page !== "diagnostics";

  const copyDiagnostics = async () => {
    try {
      await onCopyDiagnostics();
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2200);
  };

  const shellStateLabel = runtimeHealthy
    ? "运行正常"
    : connectionState === "configuration_required"
      ? "需要先完成设置"
      : "需要检查";

  return (
    <div className="desktop-frame">
      <aside className="desktop-sidebar" aria-label="灵机主导航">
        <div className="desktop-brand">
          <div className="desktop-brand-mark">灵</div>
          <div className="desktop-brand-copy">
            <strong>灵机</strong>
            <span>个人记忆操作系统</span>
          </div>
        </div>

        <nav className="desktop-nav desktop-nav-primary">
          <div className="desktop-nav-group-title">日常使用</div>
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
                <span className="desktop-nav-copy">
                  <strong>{item.label}</strong>
                  <small>{item.hint}</small>
                </span>
              </button>
            ))}
          </div>
        </nav>
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
            <div className="desktop-breadcrumb">
              灵机 / {NAVIGATION_GROUPS.find((group) => group.id === current.group)?.label}
              {advancedPage && <button className="toolbar-back-button" onClick={() => onNavigate("diagnostics")}>返回高级诊断</button>}
            </div>
            <h1>{current.label}</h1>
            <p>{current.hint}</p>
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

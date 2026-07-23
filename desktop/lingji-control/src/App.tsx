import { useState } from "react";
import AppPages from "./AppPages";
import DesktopShell from "./components/DesktopShell";
import "./DesktopUX.css";
import "./ReleaseUX.css";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { useReleaseMetadata } from "./hooks/useReleaseMetadata";
import { NAVIGATION } from "./navigation";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import { runtimeStateLabel } from "./runtimeTypes";
import type { PageId } from "./types";

export default function App() {
  const [page, setPage] = useState<PageId>("overview");
  const [inspectorTarget, setInspectorTarget] = useState<CaptureInspectorTarget | null>(null);
  const connection = useLingJiConnection();
  const release = useReleaseMetadata();
  const current = NAVIGATION.find((item) => item.id === page) ?? NAVIGATION[0];

  const openInspector = (target: CaptureInspectorTarget) => {
    setInspectorTarget(target);
    setPage("memory_inspector");
  };

  return (
    <DesktopShell
      page={page}
      current={current}
      connected={connection.connected}
      connectionState={connection.state}
      releaseMetadata={release.metadata}
      runtimeStatus={connection.runtimeStatus}
      runtimeBusy={connection.runtimeBusy}
      ownerStopped={connection.ownerStopped}
      autoRecoveryActive={connection.autoRecoveryActive}
      onNavigate={setPage}
      onRetry={() => void connection.connect()}
      onStopRuntime={() => void connection.stopRuntime()}
      onRestartRuntime={() => void connection.restartRuntime()}
      onCopyDiagnostics={() => release.copyDiagnostics(
        connection.state,
        connection.connected,
        connection.runtimeStatus,
      )}
    >
      {connection.state === "unsupported" ? (
        <section className="desktop-runtime-card desktop-runtime-card-blocked">
          <div className="desktop-runtime-symbol">桌</div>
          <div>
            <span className="desktop-eyebrow">DESKTOP ONLY</span>
            <h2>请从灵机桌面应用启动</h2>
            <p>此控制中心不提供浏览器操作入口，也不会在浏览器中保存控制令牌或连接地址。</p>
          </div>
        </section>
      ) : connection.state === "booting" ? (
        <section className="desktop-runtime-card">
          <div className="desktop-spinner" aria-hidden="true" />
          <div>
            <span className="desktop-eyebrow">AUTOMATIC RUNTIME</span>
            <h2>{runtimeStateLabel(connection.runtimeStatus)}</h2>
            <p>桌面端正在自动检查、启动并连接本机核心，不需要手动打开 PowerShell。</p>
          </div>
        </section>
      ) : (
        <>
          {!connection.connected && (
            <section className={connection.ownerStopped ? "desktop-offline-banner owner-stopped" : "desktop-offline-banner"} role="status">
              <div>
                <span className="desktop-eyebrow">{connection.ownerStopped ? "OWNER PAUSED" : "AUTO RECOVERY"}</span>
                <strong>{connection.ownerStopped ? "灵机核心已由主人停止" : connection.error || "灵机正在自动恢复连接"}</strong>
                <small>
                  {connection.ownerStopped
                    ? "后台自动恢复已暂停。恢复运行后，任务和状态同步会继续。"
                    : connection.runtimeStatus?.binary_available === false
                      ? "当前安装包没有核心 Sidecar，系统会继续检测外部8766服务。"
                      : "系统会自动重新启动或连接核心，无需重复点击按钮。"}
                </small>
              </div>
              {connection.ownerStopped && (
                <button className="button primary" disabled={Boolean(connection.runtimeBusy)} onClick={() => void connection.connect()}>
                  {connection.runtimeBusy === "ensure" ? "恢复中…" : "恢复运行"}
                </button>
              )}
            </section>
          )}
          <AppPages
            page={page}
            api={connection.api}
            connected={connection.connected}
            overview={connection.overview}
            inspectorTarget={inspectorTarget}
            onOpenInspector={openInspector}
            onNavigate={setPage}
          />
        </>
      )}
    </DesktopShell>
  );
}

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
            <span className="desktop-eyebrow">PACKAGED RUNTIME</span>
            <h2>{runtimeStateLabel(connection.runtimeStatus)}</h2>
            <p>桌面端正在检查本机8766服务；安装包包含核心时会自动启动并等待认证健康检查。</p>
          </div>
        </section>
      ) : (
        <>
          {!connection.connected && (
            <section className="desktop-offline-banner" role="status">
              <div>
                <span className="desktop-eyebrow">LOCAL CORE OFFLINE</span>
                <strong>{connection.error || runtimeStateLabel(connection.runtimeStatus)}</strong>
                <small>
                  {connection.runtimeStatus?.binary_available === false
                    ? "当前安装包没有核心 Sidecar，可以继续连接手动启动的8766服务。"
                    : `核心日志：${connection.runtimeStatus?.log_path_display ?? "owner-local LingJi logs"}`}
                </small>
              </div>
              <button className="button primary" disabled={Boolean(connection.runtimeBusy)} onClick={() => void connection.connect()}>
                {connection.runtimeBusy === "ensure" ? "启动中…" : "启动核心"}
              </button>
            </section>
          )}
          <AppPages
            page={page}
            api={connection.api}
            connected={connection.connected}
            overview={connection.overview}
            refresh={connection.connect}
            inspectorTarget={inspectorTarget}
            onOpenInspector={openInspector}
          />
        </>
      )}
    </DesktopShell>
  );
}

import { useState } from "react";
import AppPages from "./AppPages";
import DesktopShell from "./components/DesktopShell";
import "./DesktopUX.css";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { useReleaseMetadata } from "./hooks/useReleaseMetadata";
import { NAVIGATION } from "./navigation";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
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
      onNavigate={setPage}
      onRetry={() => void connection.connect()}
      onCopyDiagnostics={() => release.copyDiagnostics(connection.state, connection.connected)}
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
            <span className="desktop-eyebrow">LOCAL RUNTIME</span>
            <h2>正在连接本机灵机服务</h2>
            <p>桌面端正在读取本机凭据并检查 8766 控制服务。</p>
          </div>
        </section>
      ) : (
        <>
          {!connection.connected && (
            <section className="desktop-offline-banner" role="status">
              <div>
                <span className="desktop-eyebrow">LOCAL SERVICE OFFLINE</span>
                <strong>{connection.error || "本机控制服务暂时不可用"}</strong>
                <small>启动灵机控制服务后，桌面端会使用本机凭据重新建立连接。</small>
              </div>
              <button className="button primary" onClick={() => void connection.connect()}>重新连接</button>
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

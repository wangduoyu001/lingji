import { useState } from "react";
import { Notice } from "./components/ui";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { NAVIGATION } from "./navigation";
import AcceptancePage from "./pages/AcceptancePage";
import BackupsPage from "./pages/BackupsPage";
import BrainStatusPage from "./pages/BrainStatusPage";
import CaptureCenterPage from "./pages/CaptureCenterPage";
import CapturePage from "./pages/CapturePage";
import JobsPage from "./pages/JobsPage";
import LogsPage from "./pages/LogsPage";
import MediaPage from "./pages/MediaPage";
import MemoryInspectorPage from "./pages/MemoryInspectorPage";
import ModelsPage from "./pages/ModelsPage";
import OverviewPage from "./pages/OverviewPage";
import SettingsPage from "./pages/SettingsPage";
import StoragePage from "./pages/StoragePage";
import SystemComputePage from "./pages/SystemComputePage";
import VectorCenterPage from "./pages/VectorCenterPage";
import "./pages/VectorCenterPage.css";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import type { PageId } from "./types";

export default function App() {
  const [page, setPage] = useState<PageId>("overview");
  const [inspectorTarget, setInspectorTarget] = useState<CaptureInspectorTarget | null>(null);
  const connection = useLingJiConnection();
  const current = NAVIGATION.find((item) => item.id === page) ?? NAVIGATION[0];

  const openInspector = (target: CaptureInspectorTarget) => {
    setInspectorTarget(target);
    setPage("memory_inspector");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">灵</div><div><strong>灵机</strong><span>本地控制中心</span></div></div>
        <nav>{NAVIGATION.map((item) => <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => setPage(item.id)}><span>{item.label}</span><small>{item.hint}</small></button>)}</nav>
        <div className="sidebar-footer"><span className={connection.connected ? "status-dot online" : "status-dot"} />{connection.connected ? "本机服务已连接" : "本机服务未连接"}</div>
      </aside>
      <main className="main-area">
        <header className="topbar"><div><h1>{current.label}</h1><p>{current.hint}</p></div><div className="connection-controls"><input value={connection.baseUrl} onChange={(event) => connection.setBaseUrl(event.target.value)} aria-label="API 地址" /><input value={connection.token} onChange={(event) => connection.setToken(event.target.value)} type="password" placeholder="控制令牌" aria-label="控制令牌" /><button className="button secondary" onClick={() => void connection.connect()}>连接</button></div></header>
        {connection.error && <Notice kind="error">{connection.error}</Notice>}
        {!connection.connected && <Notice kind="warning">先启动 <code>python run_control_api.py</code>。浏览器开发模式需填写 <code>storage/control_api_token</code>。</Notice>}
        <section className="page-content">
          {page === "overview" && <OverviewPage data={connection.overview} refresh={connection.connect} />}
          {page === "brain_status" && <BrainStatusPage api={connection.api} active={connection.connected} />}
          {page === "memory_inspector" && <MemoryInspectorPage key={JSON.stringify(inspectorTarget)} api={connection.api} active={connection.connected} />}
          {page === "capture_center" && <CaptureCenterPage api={connection.api} active={connection.connected} onOpenInspector={openInspector} />}
          {page === "vector_center" && <VectorCenterPage api={connection.api} active={connection.connected} />}
          {page === "system_compute" && <SystemComputePage api={connection.api} active={connection.connected} />}
          {page === "models" && <ModelsPage api={connection.api} active={connection.connected} />}
          {page === "jobs" && <JobsPage api={connection.api} active={connection.connected} />}
          {page === "capture" && <CapturePage api={connection.api} active={connection.connected} />}
          {page === "media" && <MediaPage api={connection.api} active={connection.connected} />}
          {page === "storage" && <StoragePage api={connection.api} active={connection.connected} />}
          {page === "backups" && <BackupsPage api={connection.api} active={connection.connected} />}
          {page === "acceptance" && <AcceptancePage api={connection.api} active={connection.connected} />}
          {page === "settings" && <SettingsPage api={connection.api} active={connection.connected} />}
          {page === "logs" && <LogsPage api={connection.api} active={connection.connected} />}
        </section>
      </main>
    </div>
  );
}

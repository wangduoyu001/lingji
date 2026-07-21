import { useState } from "react";
import AppPages from "./AppPages";
import { Notice } from "./components/ui";
import "./DesktopUX.css";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { NAVIGATION, NAVIGATION_GROUPS } from "./navigation";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import type { PageId } from "./types";
export default function App() {
  const [page, setPage] = useState<PageId>("overview");
  const [inspectorTarget, setInspectorTarget] = useState<CaptureInspectorTarget | null>(null);
  const [connectionExpanded, setConnectionExpanded] = useState(false);
  const connection = useLingJiConnection();
  const current = NAVIGATION.find((item) => item.id === page) ?? NAVIGATION[0];
  const openInspector = (target: CaptureInspectorTarget) => {
    setInspectorTarget(target);
    setPage("memory_inspector");
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">灵</div>
          <div>
            <strong>灵机</strong>
            <span>个人记忆操作系统</span>
          </div>
        </div>
        <nav aria-label="主导航">
          {NAVIGATION_GROUPS.map((group) => (
            <section className="nav-group" key={group.id}>
              <div className="nav-group-title">{group.label}</div>
              {NAVIGATION.filter((item) => item.group === group.id).map((item) => (
                <button
                  key={item.id}
                  className={page === item.id ? "nav-item active" : "nav-item"}
                  onClick={() => setPage(item.id)}
                >
                  <span>{item.label}</span>
                  <small>{item.hint}</small>
                </button>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className={connection.connected ? "status-dot online" : "status-dot"} />
          {connection.connected ? "本机服务已连接" : "本机服务未连接"}
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div>
            <h1>{current.label}</h1>
            <p>{current.hint}</p>
          </div>
          <button
            className={connection.connected ? "connection-summary connected" : "connection-summary"}
            onClick={() => setConnectionExpanded((value) => !value)}
            aria-expanded={connectionExpanded}
          >
            <span className={connection.connected ? "status-dot online" : "status-dot"} />
            <span>{connection.connected ? "8766 已连接" : "配置本机连接"}</span>
            <small>{connectionExpanded ? "收起" : "展开"}</small>
          </button>
        </header>
        {connectionExpanded && (
          <section className="connection-panel" aria-label="本机服务连接设置">
            <div className="connection-controls">
              <label>API 地址<input value={connection.baseUrl} onChange={(event) => connection.setBaseUrl(event.target.value)} aria-label="API 地址" /></label>
              <label>控制令牌<input value={connection.token} onChange={(event) => connection.setToken(event.target.value)} type="password" placeholder="控制令牌" aria-label="控制令牌" /></label>
              <button className="button secondary" onClick={() => void connection.connect()}>连接并刷新</button>
            </div>
            <small>令牌仅用于本机 8766 控制 API。Tauri 环境会优先读取本地凭据，浏览器模式才需要手动填写。</small>
          </section>
        )}
        {connection.error && <Notice kind="error">{connection.error}</Notice>}
        {!connection.connected && (
          <Notice kind="warning">
            先启动 <code>python run_control_api.py</code>，再展开右上角连接栏。浏览器开发模式需要读取 <code>storage/control_api_token</code>。
          </Notice>
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
      </main>
    </div>
  );
}

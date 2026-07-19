import { useCallback, useEffect, useMemo, useState } from "react";
import App from "./App";
import AcceptancePage from "./AcceptancePage";
import { LingJiApi } from "./api";

export default function Root() {
  const [mode, setMode] = useState<"control" | "acceptance">("control");
  const api = useMemo(() => new LingJiApi(), []);
  const [baseUrl, setBaseUrl] = useState(api.baseUrl);
  const [token, setToken] = useState(api.token);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  const connect = useCallback(async () => {
    api.configure(baseUrl, token);
    try {
      await api.get("/api/overview");
      setConnected(true);
      setError("");
    } catch (reason) {
      setConnected(false);
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [api, baseUrl, token]);

  useEffect(() => {
    void (async () => {
      await api.tryTauriToken();
      setBaseUrl(api.baseUrl);
      setToken(api.token);
      try {
        await api.get("/api/overview");
        setConnected(true);
      } catch {
        setConnected(false);
      }
    })();
  }, [api]);

  return (
    <>
      <div style={{ position: "fixed", right: 16, bottom: 16, zIndex: 1000, display: "flex", gap: 8 }}>
        <button className={mode === "control" ? "button primary" : "button secondary"} onClick={() => setMode("control")}>控制中心</button>
        <button className={mode === "acceptance" ? "button primary" : "button secondary"} onClick={() => setMode("acceptance")}>环境验收</button>
      </div>
      {mode === "control" ? <App /> : (
        <main className="main-area" style={{ minHeight: "100vh" }}>
          <header className="topbar">
            <div><h1>环境验收</h1><p>真实 Vault、ChatGPT 导出、Ollama、SQLite 与媒体的只读诊断</p></div>
            <div className="connection-controls">
              <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} aria-label="API 地址" />
              <input value={token} onChange={(event) => setToken(event.target.value)} type="password" placeholder="控制令牌" aria-label="控制令牌" />
              <button className="button secondary" onClick={() => void connect()}>连接</button>
            </div>
          </header>
          {error && <div className="notice notice-error">{error}</div>}
          {!connected && <div className="notice notice-warning">请先连接本机控制 API，再执行真实环境验收。</div>}
          <section className="page-content">
            <AcceptancePage api={api} active={connected} />
          </section>
        </main>
      )}
    </>
  );
}

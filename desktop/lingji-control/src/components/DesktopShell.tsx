import { useState, type ReactNode } from "react";
import { NAVIGATION, NAVIGATION_GROUPS } from "../navigation";
import type { ReleaseMetadata } from "../hooks/useReleaseMetadata";
import type { NavigationItem, PageId } from "../types";
import NavIcon from "./NavIcon";

type Props = {
  page: PageId;
  current: NavigationItem;
  connected: boolean;
  connectionState: "booting" | "connected" | "offline" | "unsupported";
  releaseMetadata: ReleaseMetadata | null;
  onNavigate: (page: PageId) => void;
  onRetry: () => void;
  onCopyDiagnostics: () => Promise<void>;
  children: ReactNode;
};

const connectionText = {
  booting: "正在连接本机服务",
  connected: "本机服务正常",
  offline: "本机服务未连接",
  unsupported: "仅支持桌面应用",
};

export default function DesktopShell({ page, current, connected, connectionState, releaseMetadata, onNavigate, onRetry, onCopyDiagnostics, children }: Props) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const shortCommit = releaseMetadata?.commit && releaseMetadata.commit !== "development"
    ? releaseMetadata.commit.slice(0, 8)
    : "dev";

  const copyDiagnostics = async () => {
    try {
      await onCopyDiagnostics();
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2200);
  };

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

        <nav className="desktop-nav">
          {NAVIGATION_GROUPS.map((group) => (
            <section className="desktop-nav-group" key={group.id}>
              <div className="desktop-nav-group-title">{group.label}</div>
              <div className="desktop-nav-items">
                {NAVIGATION.filter((item) => item.group === group.id).map((item) => (
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
            </section>
          ))}
        </nav>

        <div className="desktop-sidebar-status">
          <div className="desktop-status-line">
            <span className={connected ? "status-dot online" : "status-dot"} />
            <div>
              <strong>{connectionText[connectionState]}</strong>
              <small>{connected ? "127.0.0.1:8766" : "本机私有连接"}</small>
            </div>
          </div>
          <div className="desktop-release-line">
            <span>v{releaseMetadata?.version ?? "0.1.0"}</span>
            <span>{releaseMetadata?.channel ?? "development"}</span>
            <span>{shortCommit}</span>
          </div>
          <div className="desktop-sidebar-actions">
            {!connected && connectionState !== "unsupported" && (
              <button className="desktop-retry-button" onClick={onRetry}>重新连接</button>
            )}
            {connectionState !== "unsupported" && (
              <button className="desktop-diagnostics-button" onClick={() => void copyDiagnostics()}>
                {copyState === "copied" ? "诊断信息已复制" : copyState === "failed" ? "复制失败" : "复制诊断信息"}
              </button>
            )}
          </div>
        </div>
      </aside>

      <main className="desktop-main">
        <header className="desktop-toolbar">
          <div className="desktop-toolbar-copy">
            <div className="desktop-breadcrumb">灵机控制中心 / {NAVIGATION_GROUPS.find((group) => group.id === current.group)?.label}</div>
            <h1>{current.label}</h1>
            <p>{current.hint}</p>
          </div>
          <div className={connected ? "desktop-connection-badge connected" : "desktop-connection-badge"}>
            <span className={connected ? "status-dot online" : "status-dot"} />
            <span>{connected ? "运行中" : "离线"}</span>
          </div>
        </header>
        <div className="desktop-content">{children}</div>
      </main>
    </div>
  );
}

import { useMemo, useState, type ReactNode } from "react";
import { runtimeStateLabel, type RuntimeBootstrapStatus, type RuntimeStatus } from "../runtimeTypes";
import type { ConnectionState } from "../hooks/useLingJiConnection";
import "../AssistantAutopilot.css";

type WorkspaceName = "production" | "acceptance";

type Props = {
  state: ConnectionState;
  connected: boolean;
  ownerStopped: boolean;
  runtimeBusy: string;
  error: string;
  runtimeStatus: RuntimeStatus | null;
  bootstrapStatus: RuntimeBootstrapStatus | null;
  onConfigure: (baseDataRoot: string, workspace: WorkspaceName) => Promise<void>;
  onResume: () => void;
  children: ReactNode;
};

export default function RuntimeBoundary({
  state,
  connected,
  ownerStopped,
  runtimeBusy,
  error,
  runtimeStatus,
  bootstrapStatus,
  onConfigure,
  onResume,
  children,
}: Props) {
  const [baseDataRoot, setBaseDataRoot] = useState("");
  const [workspace, setWorkspace] = useState<WorkspaceName>("production");
  const isMac = typeof navigator !== "undefined" && /Macintosh|Mac OS X/i.test(navigator.userAgent);
  const separator = isMac ? "/" : "\\";
  const effectiveRoot = useMemo(() => {
    const root = baseDataRoot.trim().replace(/[\\/]+$/, "");
    return root ? `${root}${separator}${workspace}` : "";
  }, [baseDataRoot, separator, workspace]);

  async function chooseDataRoot() {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: true,
        title: "选择灵机资料存放位置",
      });
      if (typeof selected === "string") setBaseDataRoot(selected);
    } catch {
      // Installed desktop builds provide the native picker. The text input
      // remains an advanced fallback for development bridges.
    }
  }

  if (state === "unsupported") {
    return (
      <section className="desktop-runtime-card desktop-runtime-card-blocked">
        <div className="desktop-runtime-symbol">桌</div>
        <div>
          <span className="desktop-eyebrow">桌面应用</span>
          <h2>请从灵机桌面应用启动</h2>
          <p>控制能力只在本机桌面应用开放，不会把本机控制令牌交给浏览器页面。</p>
        </div>
      </section>
    );
  }

  if (state === "configuration_required") {
    return (
      <section className="desktop-runtime-card desktop-runtime-card-blocked runtime-setup-card">
        <div className="desktop-runtime-symbol">存</div>
        <div className="stack">
          <div>
            <span className="desktop-eyebrow">首次使用</span>
            <h2>选择一个位置存放灵机资料</h2>
            <p>
              这里只需要选一次。灵机的记忆、索引、缓存和运行记录会集中放在这里，
              以后启动会自动使用，不需要理解 DataRoot、Qdrant 或数据库目录。
            </p>
          </div>

          <div className="runtime-simple-choice">
            <button
              className="button primary"
              disabled={Boolean(runtimeBusy)}
              onClick={() => void chooseDataRoot()}
            >
              {baseDataRoot ? "重新选择存放位置" : "选择存放位置"}
            </button>
            <small>
              {baseDataRoot
                ? `已选择：${baseDataRoot}`
                : isMac
                  ? "建议选择本机用户目录下长期可用的位置。"
                  : "为避免系统盘持续增长，建议选择空间充足的非 C 盘位置。"}
            </small>
          </div>

          {error && <small className="desktop-runtime-error">{error}</small>}

          <div className="toolbar">
            <button
              className="button primary"
              disabled={!baseDataRoot.trim() || Boolean(runtimeBusy)}
              onClick={() => onConfigure(baseDataRoot.trim(), workspace)}
            >
              {runtimeBusy === "configure" || runtimeBusy === "ensure" ? "灵机正在准备…" : "开始使用灵机"}
            </button>
          </div>

          <details className="runtime-advanced-setup">
            <summary>高级设置与验收信息</summary>
            <div className="settings-list">
              <label>
                工作空间
                <select value={workspace} onChange={(event) => setWorkspace(event.target.value as WorkspaceName)}>
                  <option value="production">日常使用</option>
                  <option value="acceptance">验收 / 测试</option>
                </select>
              </label>
              <label>
                存放路径
                <input
                  value={baseDataRoot}
                  onChange={(event) => setBaseDataRoot(event.target.value)}
                  placeholder={isMac ? "/Users/you/LingJiData" : "D:\\LingJiData"}
                />
              </label>
            </div>
            <dl className="detail-list">
              <div><dt>实际数据目录</dt><dd>{effectiveRoot || "选择位置后显示"}</dd></div>
              <div><dt>启动配置</dt><dd>{bootstrapStatus?.config_path_display || "由桌面应用自动管理"}</dd></div>
            </dl>
          </details>
        </div>
      </section>
    );
  }

  if (state === "booting") {
    return (
      <section className="desktop-runtime-card">
        <div className="desktop-spinner" aria-hidden="true" />
        <div>
          <span className="desktop-eyebrow">自动启动</span>
          <h2>{runtimeStateLabel(runtimeStatus)}</h2>
          <p>灵机正在自己检查、启动并连接本机核心，不需要打开终端或手工配置端口。</p>
        </div>
      </section>
    );
  }

  return (
    <>
      {!connected && (
        <section className={ownerStopped ? "desktop-offline-banner owner-stopped" : "desktop-offline-banner"} role="status">
          <div>
            <span className="desktop-eyebrow">{ownerStopped ? "已暂停" : "自动恢复"}</span>
            <strong>{ownerStopped ? "灵机核心已暂停" : error || "灵机正在自己恢复连接"}</strong>
            <small>
              {ownerStopped
                ? "恢复后任务和状态同步会继续。"
                : runtimeStatus?.binary_available === false
                  ? "当前安装包没有可用核心组件，详细原因可在高级工具查看。"
                  : "系统会自动重新启动或连接核心，不需要反复点击。"}
            </small>
          </div>
          {ownerStopped && (
            <button className="button primary" disabled={Boolean(runtimeBusy)} onClick={onResume}>
              {runtimeBusy === "ensure" ? "恢复中…" : "恢复运行"}
            </button>
          )}
        </section>
      )}
      {children}
    </>
  );
}

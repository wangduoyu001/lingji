import { useMemo, useState, type ReactNode } from "react";
import { runtimeStateLabel, type RuntimeBootstrapStatus, type RuntimeStatus } from "../runtimeTypes";
import type { ConnectionState } from "../hooks/useLingJiConnection";

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
  const [workspace, setWorkspace] = useState<WorkspaceName>("acceptance");
  const effectiveRoot = useMemo(() => {
    const root = baseDataRoot.trim().replace(/[\\/]+$/, "");
    return root ? `${root}\\${workspace}` : "";
  }, [baseDataRoot, workspace]);

  async function chooseDataRoot() {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: true,
        title: "选择灵机基础数据目录（禁止选择 C 盘）",
      });
      if (typeof selected === "string") setBaseDataRoot(selected);
    } catch {
      // The installed Desktop has the dialog plugin. The text field remains a
      // deliberate fallback for development bridges where the picker is absent.
    }
  }

  if (state === "unsupported") {
    return (
      <section className="desktop-runtime-card desktop-runtime-card-blocked">
        <div className="desktop-runtime-symbol">桌</div>
        <div>
          <span className="desktop-eyebrow">仅桌面端</span>
          <h2>请从灵机桌面应用启动</h2>
          <p>此控制中心不提供浏览器操作入口，也不会在浏览器中保存控制令牌或连接地址。</p>
        </div>
      </section>
    );
  }

  if (state === "configuration_required") {
    return (
      <section className="desktop-runtime-card desktop-runtime-card-blocked runtime-setup-card">
        <div className="desktop-runtime-symbol">盘</div>
        <div className="stack">
          <div>
            <span className="desktop-eyebrow">需要选择数据目录</span>
            <h2>先选择非 C 盘数据目录</h2>
            <p>
              数据库、向量、日志、缓存、原始材料和生成资产不会再静默写入 C 盘。
              LocalAppData 只保存一个很小的启动指针文件。
            </p>
          </div>

          <div className="settings-list">
            <label>
              验收环境
              <select value={workspace} onChange={(event) => setWorkspace(event.target.value as WorkspaceName)}>
                <option value="acceptance">验收环境 acceptance</option>
                <option value="production">正式环境 production</option>
              </select>
            </label>
            <label>
              基础数据目录
              <div className="toolbar">
                <input
                  value={baseDataRoot}
                  onChange={(event) => setBaseDataRoot(event.target.value)}
                  placeholder="例如 D:\\LingJiData"
                />
                <button className="button secondary" disabled={Boolean(runtimeBusy)} onClick={() => void chooseDataRoot()}>
                  选择目录
                </button>
              </div>
            </label>
          </div>

          <dl className="detail-list">
            <div><dt>实际数据根</dt><dd>{effectiveRoot || "选择目录后显示"}</dd></div>
            <div><dt>启动配置</dt><dd>{bootstrapStatus?.config_path_display || "%LOCALAPPDATA%\\LingJi\\desktop-bootstrap.json"}</dd></div>
          </dl>

          {error && <small className="desktop-runtime-error">{error}</small>}
          <div className="toolbar">
            <button
              className="button primary"
              disabled={!baseDataRoot.trim() || Boolean(runtimeBusy)}
              onClick={() => onConfigure(baseDataRoot.trim(), workspace)}
            >
              {runtimeBusy === "configure" || runtimeBusy === "ensure" ? "配置并启动中…" : "保存配置并启动核心"}
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (state === "booting") {
    return (
      <section className="desktop-runtime-card">
        <div className="desktop-spinner" aria-hidden="true" />
        <div>
          <span className="desktop-eyebrow">灵机自动运行</span>
          <h2>{runtimeStateLabel(runtimeStatus)}</h2>
          <p>桌面端正在自动检查、启动并连接本机核心，不需要手动打开 PowerShell。</p>
        </div>
      </section>
    );
  }

  return (
    <>
      {!connected && (
        <section className={ownerStopped ? "desktop-offline-banner owner-stopped" : "desktop-offline-banner"} role="status">
          <div>
            <span className="desktop-eyebrow">{ownerStopped ? "主人已暂停" : "自动恢复"}</span>
            <strong>{ownerStopped ? "灵机核心已由主人停止" : error || "灵机正在自动恢复连接"}</strong>
            <small>
              {ownerStopped
                ? "后台自动恢复已暂停。恢复运行后，任务和状态同步会继续。"
                : runtimeStatus?.binary_available === false
                  ? "当前安装包没有核心 Sidecar，系统会继续检测外部8766服务。"
                  : "系统会自动重新启动或连接核心，无需重复点击按钮。"}
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

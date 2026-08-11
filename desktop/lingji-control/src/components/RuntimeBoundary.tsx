import { useState, type ReactNode } from "react";
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
  const isMac = typeof navigator !== "undefined" && /Macintosh|Mac OS X/i.test(navigator.userAgent);

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
      // Native builds provide the picker. Manual input remains a last-resort fallback.
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
      <section className="desktop-runtime-card desktop-runtime-card-blocked runtime-setup-card runtime-fallback-card">
        <div className="desktop-runtime-symbol">修</div>
        <div className="stack">
          <div>
            <span className="desktop-eyebrow">自动准备未完成</span>
            <h2>灵机没能自动确定安全的资料目录</h2>
            <p>
              正常情况下这里不会出现，灵机会自己选择平台默认位置并继续启动。
              当前自动准备失败，你可以先让灵机重试；只有重试仍失败时才需要手动选择一次。
            </p>
          </div>

          {error && <small className="desktop-runtime-error">{error}</small>}

          <div className="toolbar runtime-fallback-actions">
            <button className="button primary" disabled={Boolean(runtimeBusy)} onClick={onResume}>
              {runtimeBusy === "ensure" ? "重新准备中…" : "让灵机重新自动准备"}
            </button>
          </div>

          <details className="runtime-advanced-setup">
            <summary>故障详情与高级设置</summary>
            <button className="button secondary" disabled={Boolean(runtimeBusy)} onClick={() => void chooseDataRoot()}>
              {baseDataRoot ? "重新选择位置" : "手动选择位置"}
            </button>
            {baseDataRoot && (
              <div className="runtime-manual-fallback">
                <small>已选择：{baseDataRoot}</small>
                <button
                  className="button primary"
                  disabled={Boolean(runtimeBusy)}
                  onClick={() => onConfigure(baseDataRoot.trim(), "production")}
                >
                  {runtimeBusy === "configure" ? "正在保存…" : "使用这个位置继续"}
                </button>
              </div>
            )}
            <div className="settings-list">
              <label>
                手动路径
                <input
                  value={baseDataRoot}
                  onChange={(event) => setBaseDataRoot(event.target.value)}
                  placeholder={isMac ? "/Users/you/LingJiData" : "D:\\LingJiData"}
                />
              </label>
            </div>
            <dl className="detail-list">
              <div><dt>启动配置</dt><dd>{bootstrapStatus?.config_path_display || "由桌面应用自动管理"}</dd></div>
              <div><dt>状态来源</dt><dd>{bootstrapStatus?.source || "未知"}</dd></div>
            </dl>
          </details>
        </div>
      </section>
    );
  }

  if (state === "booting") {
    return (
      <section className="desktop-runtime-card runtime-autopilot-boot">
        <div className="desktop-spinner" aria-hidden="true" />
        <div>
          <span className="desktop-eyebrow">灵机正在自动准备</span>
          <h2>{runtimeStateLabel(runtimeStatus)}</h2>
          <p>正在选择安全资料目录、检查核心、恢复连接并同步本机状态。正常情况下不需要你设置任何东西。</p>
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

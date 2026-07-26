import type { ReactNode } from "react";
import { runtimeStateLabel, type RuntimeStatus } from "../runtimeTypes";
import type { ConnectionState } from "../hooks/useLingJiConnection";

type Props = {
  state: ConnectionState;
  connected: boolean;
  ownerStopped: boolean;
  runtimeBusy: string;
  error: string;
  runtimeStatus: RuntimeStatus | null;
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
  onResume,
  children,
}: Props) {
  if (state === "unsupported") {
    return (
      <section className="desktop-runtime-card desktop-runtime-card-blocked">
        <div className="desktop-runtime-symbol">桌</div>
        <div>
          <span className="desktop-eyebrow">DESKTOP ONLY</span>
          <h2>请从灵机桌面应用启动</h2>
          <p>此控制中心不提供浏览器操作入口，也不会在浏览器中保存控制令牌或连接地址。</p>
        </div>
      </section>
    );
  }

  if (state === "booting") {
    return (
      <section className="desktop-runtime-card">
        <div className="desktop-spinner" aria-hidden="true" />
        <div>
          <span className="desktop-eyebrow">AUTOMATIC RUNTIME</span>
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
            <span className="desktop-eyebrow">{ownerStopped ? "OWNER PAUSED" : "AUTO RECOVERY"}</span>
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

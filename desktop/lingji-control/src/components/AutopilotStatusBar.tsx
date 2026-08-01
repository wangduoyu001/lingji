import type {
  AutopilotStatus,
  RuntimeBindingVerification,
  RuntimeBootstrapStatus,
} from "../runtimeTypes";
import "./AutopilotStatusBar.css";

const SOURCE_LABELS: Record<string, string> = {
  startup_contract: "启动契约锁定",
  automatic_safe_default: "灵机自动选择",
  owner_selection: "主人指定",
  unconfigured: "尚未配置",
};

const sourceLabel = (source: string): string =>
  (SOURCE_LABELS[source] ?? source) || "未知来源";

export default function AutopilotStatusBar({
  autopilot,
  binding,
  bootstrap,
}: {
  autopilot: AutopilotStatus;
  binding: RuntimeBindingVerification | null;
  bootstrap: RuntimeBootstrapStatus | null;
}) {
  const bindingReady = binding?.verified === true;
  const waitingAuthorization = autopilot.state === "waiting_authorization"
    || autopilot.current_action.includes("授权");

  return (
    <section className={`autopilot-status-bar ${bindingReady ? "verified" : "checking"}`} aria-live="polite">
      <div className="autopilot-status-copy">
        <span className="desktop-eyebrow">LINGJI AUTOPILOT</span>
        <strong>{autopilot.current_action}</strong>
        <small>
          UI只展示状态和进度。灵机会自动执行扫描、检测、恢复和低风险维护；
          读取真实正文、修改外部配置或写入永久记忆时才请求主人授权。
        </small>
      </div>
      <div className="autopilot-status-facts">
        <span className={`pill ${bindingReady ? "ok" : "warning"}`}>
          {bindingReady ? "DataRoot绑定已验证" : "正在核验DataRoot"}
        </span>
        <span className="pill neutral">{sourceLabel(bootstrap?.source || "")}</span>
        <span className="pill neutral">自动完成 {autopilot.completed_actions.length} 项</span>
        {autopilot.failed_actions.length > 0 && (
          <span className="pill warning">等待后台重试 {autopilot.failed_actions.length} 项</span>
        )}
        {waitingAuthorization && <span className="pill warning">等待主人授权</span>}
      </div>
      <dl className="autopilot-binding-details">
        <div>
          <dt>当前DataRoot</dt>
          <dd>{binding?.actual_data_root || bootstrap?.data_root_display || "读取中"}</dd>
        </div>
        <div>
          <dt>工作空间</dt>
          <dd>{binding?.actual_workspace || bootstrap?.active_workspace || "读取中"}</dd>
        </div>
        {bootstrap?.binding_id && (
          <div>
            <dt>绑定任务</dt>
            <dd>{bootstrap.binding_id}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}

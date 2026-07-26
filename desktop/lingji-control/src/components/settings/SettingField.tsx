import type { ReactNode } from "react";
import type { SettingDefinition } from "../../pages/settingsTypes";

type Props = {
  name: string;
  definition: SettingDefinition;
  value: unknown;
  overridden: boolean;
  dirty: boolean;
  groupLabel?: string;
  change: (value: unknown) => void;
  reset: () => void;
};

function display(value: unknown, unit?: string): string {
  if (value === undefined || value === null || value === "") return "未设置";
  const text = typeof value === "boolean" ? (value ? "开启" : "关闭") : String(value);
  return unit ? `${text} ${unit}` : text;
}

export default function SettingField({ name, definition, value, overridden, dirty, groupLabel, change, reset }: Props) {
  let input: ReactNode;
  const editable = definition.editable !== false;
  if (definition.type === "boolean") {
    input = <input disabled={!editable} type="checkbox" checked={Boolean(value)} onChange={(event) => change(event.target.checked)} />;
  } else if (definition.type === "choice") {
    input = <select disabled={!editable} value={String(value ?? "")} onChange={(event) => change(event.target.value)}>{(definition.choices ?? []).map((choice) => <option key={choice}>{choice}</option>)}</select>;
  } else {
    input = <input disabled={!editable} type={definition.type === "string" ? "text" : "number"} min={definition.minimum} max={definition.maximum} step={definition.type === "integer" ? 1 : "any"} value={String(value ?? "")} onChange={(event) => change(definition.type === "integer" ? Number.parseInt(event.target.value || "0", 10) : definition.type === "number" ? Number(event.target.value || 0) : event.target.value)} />;
  }

  const status = dirty ? "等待保存" : overridden ? "主人已修改" : "使用系统默认";
  const impacts = [
    `性能：${definition.performance_impact}`,
    `存储：${definition.storage_impact}`,
    `费用：${definition.cost_impact}`,
    `隐私：${definition.privacy_impact}`,
  ];

  return (
    <div className="setting-row">
      <div>
        <div className="toolbar">
          <strong>{definition.label}</strong>
          {groupLabel && <span className="pill neutral">{groupLabel}</span>}
          <span className={`pill ${dirty ? "warning" : overridden ? "ok" : "neutral"}`}>{status}</span>
          <span className={`pill ${definition.risk_level === "high" ? "error" : definition.risk_level === "medium" ? "warning" : "ok"}`}>风险 {definition.risk_level}</span>
          {definition.availability_state !== "available" && <span className={`pill ${definition.availability_state === "unavailable" ? "error" : "warning"}`}>{definition.availability_state === "unavailable" ? "能力不可用" : "能力未知"}</span>}
        </div>
        <code>{name}</code>
        <p>{definition.description}</p>
        <small>当前：{display(value, definition.unit)} · 默认：{display(definition.default, definition.unit)} · 推荐：{display(definition.recommended, definition.unit)}</small>
        {(definition.minimum !== undefined || definition.maximum !== undefined) && <small>范围：{definition.minimum ?? "不限"} 至 {definition.maximum ?? "不限"}{definition.unit ? ` ${definition.unit}` : ""}</small>}
        <p><strong>为什么推荐：</strong>{definition.recommendation_reason}</p>
        <p><strong>什么时候修改：</strong>{definition.when_to_change}</p>
        <p><strong>影响：</strong>{impacts.join("；")}</p>
        {definition.disabled_reason && <p><strong>能力说明：</strong>{definition.disabled_reason}</p>}
        {(definition.restart_required || definition.task_required) && <p><strong>生效方式：</strong>{definition.restart_required ? "需要重启" : "无需重启"}{definition.task_required ? "；会创建后台任务" : ""}</p>}
        {definition.learn_more && <small>{definition.learn_more}</small>}
      </div>
      <div className="setting-control">
        {input}
        <button className="button secondary" disabled={!overridden && !dirty} onClick={reset}>恢复默认</button>
      </div>
    </div>
  );
}

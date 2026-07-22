import { useEffect, useMemo, useState } from "react";
import SettingField from "../components/settings/SettingField";
import { Empty, Notice, Panel } from "../components/ui";
import type { PageProps } from "../types";
import { useSettingsController } from "./useSettingsController";

export default function SettingsPage({ api, active }: PageProps) {
  const controller = useSettingsController(api, active);
  const { snapshot, draft, dirtyValues, dirtyCount, error, message, saving } = controller;
  const [group, setGroup] = useState("");
  const [query, setQuery] = useState("");
  const [modifiedOnly, setModifiedOnly] = useState(false);
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [unavailableOnly, setUnavailableOnly] = useState(false);

  const groups = snapshot?.groups ?? [];
  useEffect(() => {
    if (groups.length && !groups.some((item) => item.id === group)) setGroup(groups[0].id);
  }, [group, groups]);

  const groupLabels = useMemo(
    () => Object.fromEntries(groups.map((item) => [item.id, item.label])),
    [groups],
  );

  if (!snapshot) return <Empty text="连接后加载设置。" />;

  const normalizedQuery = query.trim().toLowerCase();
  const globalFilter = Boolean(normalizedQuery || modifiedOnly || highRiskOnly || unavailableOnly);
  const rows = Object.entries(snapshot.definitions).filter(([key, definition]) => {
    if (!globalFilter && definition.group !== group) return false;
    const overridden = Object.prototype.hasOwnProperty.call(snapshot.overrides, key);
    const dirty = Object.prototype.hasOwnProperty.call(dirtyValues, key);
    if (modifiedOnly && !overridden && !dirty) return false;
    if (highRiskOnly && definition.risk_level !== "high") return false;
    if (unavailableOnly && definition.availability_state === "available") return false;
    if (!normalizedQuery) return true;
    return [
      key,
      definition.label,
      definition.description,
      definition.when_to_change,
      definition.recommendation_reason,
      groupLabels[definition.group],
    ].some((value) => String(value || "").toLowerCase().includes(normalizedQuery));
  });
  const groupKeys = Object.entries(snapshot.definitions)
    .filter(([, definition]) => definition.group === group)
    .map(([key]) => key);
  const title = globalFilter ? `设置筛选结果 · ${rows.length}` : `设置 · ${groupLabels[group] || group}`;

  return (
    <div className="stack">
      <Notice>设置默认值、推荐值、分组、风险和能力状态全部来自后端 Registry。高风险变更会先生成影响预览，再要求主人确认。</Notice>
      {error && <Notice kind="error">{error}</Notice>}
      {message && <Notice>{message}</Notice>}
      <div className="toolbar">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索全部设置、说明、分组或参数键" aria-label="搜索设置" />
        <label><input type="checkbox" checked={modifiedOnly} onChange={(event) => setModifiedOnly(event.target.checked)} /> 只看已修改</label>
        <label><input type="checkbox" checked={highRiskOnly} onChange={(event) => setHighRiskOnly(event.target.checked)} /> 只看高风险</label>
        <label><input type="checkbox" checked={unavailableOnly} onChange={(event) => setUnavailableOnly(event.target.checked)} /> 只看不可用</label>
        <span>{dirtyCount ? `${dirtyCount} 项等待保存` : "没有未保存修改"}</span>
      </div>
      <div className="toolbar">
        <span>设置 {snapshot.summary.setting_count}</span>
        <span>主人覆盖 {snapshot.summary.override_count}</span>
        <span>高风险 {snapshot.summary.high_risk_count}</span>
        <span>能力不可用 {snapshot.summary.unavailable_count}</span>
      </div>
      <div className="settings-layout">
        <div className="settings-groups">
          {groups.map((item) => (
            <button className={item.id === group && !globalFilter ? "active" : ""} key={item.id} onClick={() => {
              setGroup(item.id);
              setQuery("");
              setModifiedOnly(false);
              setHighRiskOnly(false);
              setUnavailableOnly(false);
            }}>
              <strong>{item.label}</strong>
              <small>{item.description}</small>
              <small>{item.setting_count} 项</small>
            </button>
          ))}
        </div>
        <Panel title={title}>
          <div className="settings-list">
            {rows.length ? rows.map(([key, definition]) => (
              <SettingField
                key={key}
                name={key}
                definition={definition}
                value={draft[key]}
                groupLabel={globalFilter ? groupLabels[definition.group] : undefined}
                overridden={Object.prototype.hasOwnProperty.call(snapshot.overrides, key)}
                dirty={Object.prototype.hasOwnProperty.call(dirtyValues, key)}
                change={(value) => controller.change(key, value)}
                reset={() => void controller.reset([key])}
              />
            )) : <Empty text="当前筛选条件下没有设置。" />}
          </div>
          <div className="toolbar sticky-actions">
            <button className="button primary" disabled={saving || dirtyCount === 0} onClick={() => void controller.save()}>{saving ? "处理中…" : "预览并保存修改"}</button>
            <button className="button secondary" disabled={saving || groupKeys.length === 0} onClick={() => void controller.reset(groupKeys)}>恢复本组默认</button>
            <button className="button secondary" disabled={saving || dirtyCount === 0} onClick={controller.cancelDraft}>取消未保存修改</button>
            <button className="button secondary" disabled={saving} onClick={() => void controller.reload()}>重新加载</button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import SettingField from "../components/settings/SettingField";
import { Empty, Notice, Panel } from "../components/ui";
import type { PageProps, SettingsSnapshot } from "../types";

const GROUP_LABELS: Record<string, string> = {
  media_processing: "媒体处理",
  extraction: "采集与提取",
  storage: "存储与生命周期",
  backup: "备份与恢复",
  memory: "记忆与检索",
  control: "本地控制",
  runtime: "运行环境",
};

export default function SettingsPage({ api, active }: PageProps) {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot | null>(null);
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [group, setGroup] = useState("");
  const [query, setQuery] = useState("");
  const [modifiedOnly, setModifiedOnly] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!active) return;
    try {
      const next = await api.get<SettingsSnapshot>("/api/settings");
      setSnapshot(next);
      setDraft(next.values);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  const groups = useMemo(() => snapshot ? Array.from(new Set(Object.values(snapshot.definitions).map((item) => item.group))) : [], [snapshot]);
  useEffect(() => {
    if (groups.length && !groups.includes(group)) setGroup(groups[0]);
  }, [group, groups]);

  if (!snapshot) return <Empty text="连接后加载设置。" />;

  const isDirty = (key: string) => !Object.is(draft[key], snapshot.values[key]);
  const normalizedQuery = query.trim().toLowerCase();
  const rows = Object.entries(snapshot.definitions).filter(([key, definition]) => {
    if (definition.group !== group) return false;
    const overridden = Object.prototype.hasOwnProperty.call(snapshot.overrides, key);
    if (modifiedOnly && !overridden && !isDirty(key)) return false;
    if (!normalizedQuery) return true;
    return [key, definition.label, definition.description, definition.when_to_change, definition.recommendation_reason]
      .some((value) => String(value || "").toLowerCase().includes(normalizedQuery));
  });
  const dirtyCount = Object.keys(snapshot.definitions).filter(isDirty).length;

  async function save() {
    setSaving(true);
    setError("");
    try {
      const next = await api.patch<SettingsSnapshot>("/api/settings", { values: draft });
      setSnapshot(next);
      setDraft(next.values);
      setMessage("设置已保存。涉及后台任务或重启的设置会在说明中明确提示。");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }

  async function reset(keys: string[]) {
    setSaving(true);
    setError("");
    try {
      const next = await api.post<SettingsSnapshot>("/api/settings/reset", { keys });
      setSnapshot(next);
      setDraft(next.values);
      setMessage(`已恢复 ${keys.length} 项系统默认值。`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <Notice>所有可由主人决定的默认值都必须在这里或对应功能页显示当前值、默认值、推荐值、影响和恢复入口。不可编辑的内部常量只提供说明，不伪装成设置。</Notice>
      {error && <Notice kind="error">{error}</Notice>}
      {message && <Notice>{message}</Notice>}
      <div className="toolbar">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索设置名称、说明或参数键" aria-label="搜索设置" />
        <label><input type="checkbox" checked={modifiedOnly} onChange={(event) => setModifiedOnly(event.target.checked)} /> 只显示已修改</label>
        <span>{dirtyCount ? `${dirtyCount} 项等待保存` : "没有未保存修改"}</span>
      </div>
      <div className="settings-layout">
        <div className="settings-groups">{groups.map((item) => <button className={item === group ? "active" : ""} key={item} onClick={() => setGroup(item)}><strong>{GROUP_LABELS[item] || item}</strong><small>{item}</small></button>)}</div>
        <Panel title={`设置 · ${GROUP_LABELS[group] || group}`}>
          <div className="settings-list">
            {rows.length ? rows.map(([key, definition]) => <SettingField key={key} name={key} definition={definition} value={draft[key]} overridden={Object.prototype.hasOwnProperty.call(snapshot.overrides, key)} dirty={isDirty(key)} change={(value) => { setMessage(""); setDraft({ ...draft, [key]: value }); }} reset={() => void reset([key])} />) : <Empty text="当前筛选条件下没有设置。" />}
          </div>
          <div className="toolbar sticky-actions">
            <button className="button primary" disabled={saving || dirtyCount === 0} onClick={() => void save()}>{saving ? "处理中…" : "保存修改"}</button>
            <button className="button secondary" disabled={saving || rows.length === 0} onClick={() => void reset(rows.map(([key]) => key))}>恢复本组默认</button>
            <button className="button secondary" disabled={saving || dirtyCount === 0} onClick={() => setDraft(snapshot.values)}>取消未保存修改</button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

import type { ReactNode } from "react";

export function bytes(value: unknown): string {
  let size = Number(value || 0);
  if (size < 1024) return `${size} B`;
  const units = ["KB", "MB", "GB", "TB", "PB"];
  let index = -1;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 100 ? 0 : size >= 10 ? 1 : 2)} ${units[index]}`;
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="panel"><h2>{title}</h2><div className="panel-body">{children}</div></section>;
}

export function Notice({ kind = "info", children }: { kind?: "info" | "error" | "warning"; children: ReactNode }) {
  return <div className={`notice notice-${kind}`}>{children}</div>;
}

export function Metric({ title, value, detail = "", tone = "neutral" }: { title: string; value: string; detail?: string; tone?: string }) {
  return <div className={`metric metric-${tone}`}><span>{title}</span><strong>{value}</strong><small>{detail}</small></div>;
}

export function Empty({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

export function Json({ value }: { value: unknown }) {
  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}

import type { LingJiApi } from "./api";

export type Row = Record<string, any>;

export type PageId =
  | "overview"
  | "system_compute"
  | "jobs"
  | "capture"
  | "media"
  | "storage"
  | "backups"
  | "acceptance"
  | "settings"
  | "logs";

export type NavigationItem = {
  id: PageId;
  label: string;
  hint: string;
};

export type PageProps = {
  api: LingJiApi;
  active: boolean;
};

export type SettingDefinition = {
  group: string;
  label: string;
  description: string;
  type: "integer" | "number" | "boolean" | "string" | "choice";
  default: unknown;
  recommended?: unknown;
  recommendation_reason?: string;
  when_to_change?: string;
  minimum?: number;
  maximum?: number;
  choices?: string[];
  unit?: string;
  scope?: string;
  restart_required?: boolean;
  task_required?: boolean;
  risk_level?: "low" | "medium" | "high";
  cost_impact?: string;
  storage_impact?: string;
  performance_impact?: string;
  privacy_impact?: string;
  dependencies?: string[];
  conflicts?: string[];
  learn_more?: string;
  editable?: boolean;
};

export type SettingsSnapshot = {
  values: Record<string, any>;
  overrides: Record<string, any>;
  definitions: Record<string, SettingDefinition>;
};

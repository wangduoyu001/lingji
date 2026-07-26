export type SettingRiskLevel = "low" | "medium" | "high";
export type SettingAvailability = "available" | "unavailable" | "unknown";

export type SettingDefinition = {
  group: string;
  label: string;
  description: string;
  type: "integer" | "number" | "boolean" | "string" | "choice";
  default: unknown;
  recommended: unknown;
  recommendation_reason: string;
  when_to_change: string;
  performance_impact: string;
  storage_impact: string;
  cost_impact: string;
  privacy_impact: string;
  risk_level: SettingRiskLevel;
  availability_state: SettingAvailability;
  disabled_reason?: string | null;
  confirmation_required: boolean;
  editable: boolean;
  minimum?: number;
  maximum?: number;
  choices?: string[];
  max_length?: number;
  unit?: string;
  scope?: string;
  restart_required?: boolean;
  task_required?: boolean;
  dependencies?: string[];
  conflicts?: string[];
  learn_more?: string;
};

export type SettingGroup = {
  id: string;
  label: string;
  description: string;
  order: number;
  setting_count: number;
};

export type SettingsSnapshot = {
  schema_version: number;
  values: Record<string, unknown>;
  overrides: Record<string, unknown>;
  definitions: Record<string, SettingDefinition>;
  groups: SettingGroup[];
  summary: {
    setting_count: number;
    override_count: number;
    high_risk_count: number;
    unavailable_count: number;
  };
  confirmation_phrase: string;
};

export type SettingChange = {
  key: string;
  label: string;
  group: string;
  from: unknown;
  to: unknown;
  default: unknown;
  recommended: unknown;
  risk_level: SettingRiskLevel;
  confirmation_required: boolean;
  restart_required: boolean;
  task_required: boolean;
  availability_state: SettingAvailability;
  disabled_reason?: string | null;
  impacts: {
    performance: string;
    storage: string;
    cost: string;
    privacy: string;
  };
};

export type SettingsChangePreview = {
  changes: SettingChange[];
  normalized_values: Record<string, unknown>;
  change_count: number;
  high_risk_changes: SettingChange[];
  requires_confirmation: boolean;
  confirmation_phrase: string | null;
  errors: string[];
  warnings: string[];
  can_commit: boolean;
};

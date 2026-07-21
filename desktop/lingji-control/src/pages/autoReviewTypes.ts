export type AutoReviewMode = "OFF" | "SHADOW" | "ACTIVE" | string;

export type AutoReviewStatus = {
  mode: AutoReviewMode;
  active_supported: boolean;
  mutation_enabled: boolean;
  ai_enabled: boolean;
  ai_provider: string;
  primary_model: string | null;
  fallback_model: string | null;
  decision_count: number;
};

export type AutoReviewFinding = {
  code: string;
  message: string;
  risk_points: number;
  hard_manual?: boolean;
  blocked?: boolean;
  reversible?: boolean;
  evidence?: string[];
};

export type AutoReviewDecision = {
  decision_id: string;
  candidate_id: string;
  mode: AutoReviewMode;
  action: string;
  risk_level: string;
  risk_score: number;
  reasons: AutoReviewFinding[];
  target_memory_id?: string | null;
  reversible: boolean;
  mutation_performed: boolean;
};

export type AutoReviewAudit = {
  schema_version: number;
  evaluated_at: string;
  previous_hash: string;
  event_hash: string;
  decision: AutoReviewDecision;
  mutation_performed: boolean;
  ai_assessment?: {
    model?: string | null;
    risk_points?: number;
    flags?: string[];
    summary?: string;
    available?: boolean;
    error?: string | null;
  } | null;
};

export type AutoReviewDecisionPage = {
  items: AutoReviewAudit[];
  total: number;
  limit: number;
};

export type AutoReviewMetrics = {
  total: number;
  actions: Record<string, number>;
  risk_levels: Record<string, number>;
  ai_assessed: number;
  mutation_count: number;
};

export type WorkActor = "system" | "owner" | "external";

export type WorkItem = {
  work_id: string;
  title: string;
  source_id?: string | null;
  status: string;
  owner_approved?: boolean;
  created_at?: string;
  updated_at?: string | null;
};

export type ExecutionEvent = {
  event_id: string;
  work_id: string;
  event_type: string;
  detail?: Record<string, unknown>;
  created_at?: string;
};

export type Outcome = {
  work_id: string;
  status: string;
  summary: string;
  evidence?: Record<string, unknown>;
  created_at?: string;
};

export type NextAction = {
  action_id: string;
  work_id: string;
  description: string;
  actor: WorkActor;
  created_at?: string;
};

export type PendingAction = {
  action_id: string;
  work_id: string;
  description: string;
  actor: WorkActor;
  resolved: boolean;
  created_at?: string;
};

export type PendingActionsResponse = {
  pending_actions?: PendingAction[];
};

/** A missing list is an unknown read, not evidence that there are no actions. */
export function pendingActionsFrom(response: PendingActionsResponse | null | undefined): PendingAction[] | null {
  return Array.isArray(response?.pending_actions) ? response.pending_actions : null;
}

export type Failure = {
  failure_id: string;
  work_id: string;
  stage: string;
  reason: string;
  retryable: boolean;
  created_at?: string;
};

export type WorkFact = {
  work: WorkItem | null;
  events: ExecutionEvent[];
  outcome: Outcome | null;
  next_action: NextAction | null;
  pending_actions: PendingAction[];
  failure: Failure | null;
};

export type WorkSummary = {
  phase?: string | null;
  result?: string | null;
  time?: string | null;
  source?: string | null;
  source_id?: string | null;
  next_actor?: string | null;
};

export type WorkHistoryItem = WorkFact & { summary?: WorkSummary | null };

export type WorkHistoryResponse = {
  ["items"]: WorkHistoryItem[];
  limit?: number;
  offset?: number;
  total?: number | null;
  has_more?: boolean;
};

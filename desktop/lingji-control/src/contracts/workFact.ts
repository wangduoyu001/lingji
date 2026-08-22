export type WorkActor = "system" | "owner" | "external" | "none";
export type WorkStatus = "pending" | "accepted" | "running" | "completed" | "failed" | "skipped";
export type OutcomeStatus = "success" | "failure" | "skipped";

export type WorkItem = {
  work_id: string;
  title: string;
  source_id: string | null;
  status: WorkStatus;
  owner_approved: boolean;
  created_at: string;
  updated_at: string;
};

export type ExecutionEvent = {
  event_id: string;
  work_id: string;
  event_type: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type Outcome = {
  work_id: string;
  status: OutcomeStatus;
  summary: string;
  evidence: Record<string, unknown>;
  completed_at: string;
};

export type NextAction = {
  work_id: string;
  actor: WorkActor;
  description: string;
};

export type PendingAction = {
  action_id: string;
  work_id: string;
  description: string;
  reason: string | null;
  resolved: boolean;
  created_at: string;
  resolved_at: string | null;
};

export type CurrentWorkFact = {
  work: WorkItem | null;
  events: ExecutionEvent[];
  outcome: Outcome | null;
  next_action: NextAction | null;
  pending_actions: PendingAction[];
};

export type RecentWorkFact = {
  work_items: WorkItem[];
};

export type WorkDetailFact = CurrentWorkFact;

export type WorkTimelineFact = {
  work_id: string;
  events: ExecutionEvent[];
};

export type PendingActionsFact = {
  pending_actions: PendingAction[];
};

export function formatWorkDetail(detail: Record<string, unknown> | null | undefined): string {
  if (!detail || Object.keys(detail).length === 0) return "无附加信息";
  try {
    return JSON.stringify(detail);
  } catch {
    return "事件详情不可显示";
  }
}

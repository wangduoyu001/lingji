export type WorkActor = "system" | "owner" | "external";

export type WorkItem = {
  id: string;
  title: string;
  status: "queued" | "running" | "completed" | "failed";
  updated_at?: string;
};

export type ExecutionEvent = {
  id: string;
  work_id: string;
  event: string;
  detail?: string;
  created_at?: string;
};

export type Outcome = {
  status: "success" | "failure" | "skipped";
  summary: string;
};

export type NextAction = {
  actor: WorkActor;
  summary: string;
};

export type PendingAction = {
  id: string;
  summary: string;
  reason: string;
};

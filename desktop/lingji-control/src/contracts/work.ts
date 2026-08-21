export type WorkFactItem = {
  id: string;
  title: string;
  status: string;
  nextActor?: "system" | "owner" | "external";
};

export type PendingAction = {
  id: string;
  title: string;
  reason?: string;
};

export type WorkTimelineEvent = {
  id: string;
  type: string;
  message: string;
  createdAt?: string;
};

export type CurrentWorkResponse = {
  items: WorkFactItem[];
};

export type PendingActionsResponse = {
  items: PendingAction[];
};

export type WorkTimelineResponse = {
  work_id: string;
  events: WorkTimelineEvent[];
};

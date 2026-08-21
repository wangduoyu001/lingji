import type {
  CurrentWorkResponse,
  PendingActionsResponse,
  WorkTimelineResponse,
} from "./contracts/work";
import { lingJiApi } from "./api";

export const workApi = {
  current: () => lingJiApi.get<CurrentWorkResponse>("/v1/work/current"),
  pendingActions: () => lingJiApi.get<PendingActionsResponse>("/v1/work/pending-actions"),
  timeline: (workId: string) =>
    lingJiApi.get<WorkTimelineResponse>(`/v1/work/timeline/${workId}`),
};

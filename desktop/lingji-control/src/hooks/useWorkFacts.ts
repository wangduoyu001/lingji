import { useCallback, useEffect, useState } from "react";
import type { LingJiApi } from "../api";
import type { PendingAction, WorkItem } from "../contracts/work";

export function useWorkFacts(api: LingJiApi, active: boolean) {
  const [current, setCurrent] = useState<WorkItem[]>([]);
  const [pending, setPending] = useState<PendingAction[]>([]);

  const refresh = useCallback(async () => {
    if (!active) return;
    const [work, actions] = await Promise.all([
      api.get<{ items: WorkItem[] }>("/v1/work/current"),
      api.get<{ items: PendingAction[] }>("/v1/work/pending-actions"),
    ]);
    setCurrent(work.items ?? []);
    setPending(actions.items ?? []);
  }, [api, active]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { current, pending, refresh };
}

import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import type { LingJiApi } from "../api";
import { decideOnboardingRoute } from "../pages/memorySourcesApi";
import type { PageId } from "../types";

type OnboardingProps = {
  api: LingJiApi;
  connected: boolean;
  page: PageId;
  setPage: Dispatch<SetStateAction<PageId>>;
};

export function useMemorySourcesOnboarding({ api, connected, page, setPage }: OnboardingProps): void {
  const [attempt, setAttempt] = useState(0);
  const checkedRef = useRef(false);
  const pageRef = useRef(page);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const connectedRef = useRef(connected);
  const mountedRef = useRef(false);

  useEffect(() => { pageRef.current = page; }, [page]);
  useEffect(() => { connectedRef.current = connected; }, [connected]);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    if (!connected) {
      retryRef.current = 0;
      return;
    }
    if (checkedRef.current) return;
    void Promise.all([
      api.get<Array<{ status?: string; kind?: string }>>("/api/automatic-memory/sources"),
      api.get<Array<{ status?: string; kind?: string }>>("/api/automatic-memory/discovered"),
    ]).then(([authorized, discovered]) => {
      if (!mountedRef.current || !connectedRef.current) return;
      checkedRef.current = true;
      retryRef.current = 0;
      const destination = decideOnboardingRoute({ page: pageRef.current, checked: false, readsSucceeded: true, authorized, discovered });
      if (destination) setPage(destination);
    }).catch(() => {
      // A transient source-read failure must not mark onboarding complete.
      if (!mountedRef.current || !connectedRef.current) return;
      retryRef.current += 1;
      const delay = Math.min(250 * (2 ** Math.min(retryRef.current - 1, 5)), 8_000);
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        if (mountedRef.current && connectedRef.current && !checkedRef.current) setAttempt((value) => value + 1);
      }, delay);
    });
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [api, connected, attempt, setPage]);
}

import { useCallback, useEffect, useRef, useState } from "react";
import { toResourceError, type PollingSnapshot, type ResourceError } from "../contracts/resourceState";

export type PollingResourceOptions<T> = {
  fetcher: (signal: AbortSignal) => Promise<T>;
  enabled?: boolean;
  intervalMs?: number;
  immediate?: boolean;
  staleAfterMs?: number;
  pauseWhenHidden?: boolean;
  maxBackoffMs?: number;
};

export type PollingResourceResult<T> = PollingSnapshot<T> & {
  paused: boolean;
  refresh: (options?: { force?: boolean }) => Promise<void>;
  pause: () => void;
  resume: () => void;
};

export function ownsRequest(current: unknown, candidate: unknown): boolean {
  return current === candidate;
}

export function canPublishRequest(current: unknown, candidate: unknown, aborted: boolean): boolean {
  return !aborted && ownsRequest(current, candidate);
}

export function shouldScheduleHiddenActivation({ hidden, manuallyPaused, activationRead }: { hidden: boolean; manuallyPaused: boolean; activationRead: boolean }): boolean {
  return hidden && !manuallyPaused && !activationRead;
}

const INITIAL_STATE = {
  data: null,
  loading: false,
  refreshing: false,
  stale: false,
  error: null,
  lastSuccessAt: null,
  lastAttemptAt: null,
  failureCount: 0,
} as const;

function isAbortReason(reason: unknown): boolean {
  if (reason instanceof DOMException && reason.name === "AbortError") return true;
  if (reason && typeof reason === "object") {
    const candidate = reason as { name?: unknown; code?: unknown };
    return candidate.name === "AbortError" || candidate.code === "REQUEST_CANCELLED";
  }
  return false;
}

function ageIsStale(lastSuccessAt: string | null, staleAfterMs: number): boolean {
  if (!lastSuccessAt) return false;
  const parsed = Date.parse(lastSuccessAt);
  return Number.isFinite(parsed) && Date.now() - parsed > staleAfterMs;
}

export function usePollingResource<T>(options: PollingResourceOptions<T>): PollingResourceResult<T> {
  const {
    fetcher,
    enabled = true,
    intervalMs = 10_000,
    immediate = true,
    staleAfterMs = Math.max(intervalMs * 2, 30_000),
    pauseWhenHidden = true,
    maxBackoffMs = 120_000,
  } = options;

  const [state, setState] = useState<PollingSnapshot<T>>(INITIAL_STATE);
  const [manuallyPaused, setManuallyPaused] = useState(false);
  const [hidden, setHidden] = useState(() => typeof document !== "undefined" && document.hidden);
  const mountedRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const staleTimerRef = useRef<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const inFlightRef = useRef<Promise<void> | null>(null);
  const requestIdentityRef = useRef<object | null>(null);
  const activationReadRef = useRef(false);
  const failureCountRef = useRef(0);
  const lastErrorRef = useRef<ResourceError | null>(null);
  const lastSuccessAtRef = useRef<string | null>(null);

  const clearPollTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const refresh = useCallback(async (options: { force?: boolean } = {}): Promise<void> => {
    if (!enabled) return;
    if (inFlightRef.current && !options.force) return inFlightRef.current;
    if (options.force) {
      controllerRef.current?.abort();
      inFlightRef.current = null;
    }

    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    const attemptedAt = new Date().toISOString();

    const requestIdentity = {};
    requestIdentityRef.current = requestIdentity;
    const request = (async () => {
      setState((current) => ({
        ...current,
        loading: current.data === null,
        refreshing: current.data !== null,
        lastAttemptAt: attemptedAt,
      }));
      try {
        const data = await fetcher(controller.signal);
        if (!mountedRef.current || !canPublishRequest(requestIdentityRef.current, requestIdentity, controller.signal.aborted)) return;
        const succeededAt = new Date().toISOString();
        failureCountRef.current = 0;
        lastErrorRef.current = null;
        lastSuccessAtRef.current = succeededAt;
        setState({
          data,
          loading: false,
          refreshing: false,
          stale: false,
          error: null,
          lastSuccessAt: succeededAt,
          lastAttemptAt: attemptedAt,
          failureCount: 0,
        });
      } catch (reason) {
        if (!mountedRef.current || !canPublishRequest(requestIdentityRef.current, requestIdentity, controller.signal.aborted) || isAbortReason(reason)) return;
        const error = toResourceError(reason);
        const failureCount = failureCountRef.current + 1;
        failureCountRef.current = failureCount;
        lastErrorRef.current = error;
        setState((current) => ({
          ...current,
          loading: false,
          refreshing: false,
          stale: ageIsStale(lastSuccessAtRef.current, staleAfterMs),
          error,
          lastAttemptAt: attemptedAt,
          failureCount,
        }));
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null;
        if (ownsRequest(requestIdentityRef.current, requestIdentity)) {
          inFlightRef.current = null;
          requestIdentityRef.current = null;
        }
      }
    })();

    inFlightRef.current = request;
    return request;
  }, [enabled, fetcher, staleAfterMs]);

  const pause = useCallback(() => setManuallyPaused(true), []);
  const resume = useCallback(() => setManuallyPaused(false), []);
  const hiddenPaused = pauseWhenHidden && hidden;
  const effectivelyPaused = manuallyPaused || hiddenPaused;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearPollTimer();
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [clearPollTimer]);

  useEffect(() => {
    if (!pauseWhenHidden || typeof document === "undefined") return;
    const onVisibilityChange = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [pauseWhenHidden]);

  useEffect(() => {
    if (!enabled) {
      activationReadRef.current = false;
      clearPollTimer();
      controllerRef.current?.abort();
      setState((current) => ({ ...current, loading: false, refreshing: false }));
      return;
    }
    const needsActivationRead = !activationReadRef.current;
    if (effectivelyPaused) {
      clearPollTimer();
      // A hidden document may be the first active view after navigation. Do
      // one real read for that activation, then let visibility pause cadence.
      if (shouldScheduleHiddenActivation({ hidden, manuallyPaused, activationRead: activationReadRef.current })) {
        // Use a cancellable timer so React StrictMode's setup/cleanup probe
        // cannot abort the only activation request before the second setup.
        timerRef.current = window.setTimeout(() => {
          timerRef.current = null;
          activationReadRef.current = true;
          void refresh({ force: true });
        }, 0);
      }
      return () => clearPollTimer();
    }
    activationReadRef.current = true;

    let cancelled = false;
    const normalInterval = Math.max(intervalMs, 250);
    const maximumBackoff = Math.max(maxBackoffMs, normalInterval);

    const schedule = (delay: number) => {
      clearPollTimer();
      timerRef.current = window.setTimeout(async () => {
        await refresh();
        if (cancelled || !mountedRef.current) return;
        const status = lastErrorRef.current?.status;
        const authBackoff = status === 401 || status === 403;
        const failures = failureCountRef.current;
        const backoff = authBackoff
          ? maximumBackoff
          : Math.min(normalInterval * (2 ** Math.max(failures, 0)), maximumBackoff);
        schedule(failures > 0 ? backoff : normalInterval);
      }, Math.max(delay, 0));
    };

    const staleOnResume = ageIsStale(lastSuccessAtRef.current, staleAfterMs);
    schedule(immediate || staleOnResume ? 0 : normalInterval);
    return () => {
      cancelled = true;
      clearPollTimer();
    };
  }, [clearPollTimer, effectivelyPaused, enabled, hidden, immediate, intervalMs, manuallyPaused, maxBackoffMs, refresh, staleAfterMs]);

  useEffect(() => {
    if (!enabled) return;
    const cadence = Math.max(Math.min(staleAfterMs, 1_000), 250);
    staleTimerRef.current = window.setInterval(() => {
      const stale = ageIsStale(lastSuccessAtRef.current, staleAfterMs);
      setState((current) => current.stale === stale ? current : { ...current, stale });
    }, cadence);
    return () => {
      if (staleTimerRef.current !== null) {
        window.clearInterval(staleTimerRef.current);
        staleTimerRef.current = null;
      }
    };
  }, [enabled, staleAfterMs]);

  return {
    ...state,
    paused: effectivelyPaused,
    refresh,
    pause,
    resume,
  };
}

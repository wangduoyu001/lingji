export type ResourceAvailability =
  | "healthy"
  | "busy"
  | "degraded"
  | "unavailable"
  | "disabled"
  | "configuration_required"
  | "unknown";

export type ResourceError = {
  code?: string;
  message: string;
  status?: number;
  retryable?: boolean;
  occurredAt?: string;
};

export type PollingSnapshot<T> = {
  data: T | null;
  loading: boolean;
  refreshing: boolean;
  stale: boolean;
  error: ResourceError | null;
  lastSuccessAt: string | null;
  lastAttemptAt: string | null;
  failureCount: number;
};

export function toResourceError(reason: unknown): ResourceError {
  if (reason instanceof Error) {
    const candidate = reason as Error & { code?: unknown; status?: unknown };
    const status = typeof candidate.status === "number" ? candidate.status : undefined;
    return {
      code: candidate.code ? String(candidate.code) : undefined,
      message: candidate.message,
      status,
      retryable: status === undefined || status === 0 || status >= 500,
      occurredAt: new Date().toISOString(),
    };
  }
  return {
    message: String(reason || "Unknown resource error"),
    retryable: true,
    occurredAt: new Date().toISOString(),
  };
}

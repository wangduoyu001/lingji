import { useCallback, useEffect, useMemo, useState } from "react";
import { LingJiApi } from "../api";
import type { Row } from "../types";

export function useLingJiConnection() {
  const api = useMemo(() => new LingJiApi(), []);
  const [baseUrl, setBaseUrl] = useState(api.baseUrl);
  const [token, setToken] = useState(api.token);
  const [connected, setConnected] = useState(false);
  const [overview, setOverview] = useState<Row | null>(null);
  const [error, setError] = useState("");

  const connect = useCallback(async () => {
    api.configure(baseUrl, token);
    try {
      const next = await api.get<Row>("/api/overview");
      setOverview(next);
      setConnected(true);
      setError("");
    } catch (reason) {
      setConnected(false);
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [api, baseUrl, token]);

  useEffect(() => {
    void (async () => {
      await api.tryTauriToken();
      setBaseUrl(api.baseUrl);
      setToken(api.token);
      try {
        setOverview(await api.get<Row>("/api/overview"));
        setConnected(true);
      } catch {
        setConnected(false);
      }
    })();
  }, [api]);

  useEffect(() => {
    if (!connected) return;
    const timer = window.setInterval(() => {
      void api.get<Row>("/api/overview").then(setOverview).catch(() => setConnected(false));
    }, 10000);
    return () => window.clearInterval(timer);
  }, [api, connected]);

  return {
    api,
    baseUrl,
    setBaseUrl,
    token,
    setToken,
    connected,
    overview,
    error,
    connect,
  };
}

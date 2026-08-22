import { useMemo, useState } from "react";
import AppPages from "./AppPages";
import { LingJiApi } from "./api";
import DesktopShell from "./components/DesktopShell";
import QuickCapture from "./components/QuickCapture";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { usePlatformInfo } from "./hooks/usePlatformInfo";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import type { PageId } from "./types";
import "./App.css";

export default function App() {
  const api = useMemo(() => new LingJiApi(), []);
  const [page, setPage] = useState<PageId>("overview");
  const [inspectorTarget, setInspectorTarget] = useState<CaptureInspectorTarget | null>(null);
  const connection = useLingJiConnection(api);
  const platform = usePlatformInfo();

  const onOpenInspector = (target: CaptureInspectorTarget) => {
    setInspectorTarget(target);
    setPage("memory_inspector");
  };

  return (
    <DesktopShell
      page={page}
      onNavigate={setPage}
      connected={connection.connected}
      connecting={connection.connecting}
      error={connection.error}
      onRetry={() => void connection.retry()}
      platform={platform}
    >
      <QuickCapture api={api} active={connection.connected} onNavigate={setPage} />
      <AppPages
        page={page}
        api={api}
        connected={connection.connected}
        overview={connection.overview}
        inspectorTarget={inspectorTarget}
        onOpenInspector={onOpenInspector}
        onNavigate={setPage}
      />
    </DesktopShell>
  );
}

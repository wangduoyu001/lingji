import { useState } from "react";
import AppPages from "./AppPages";
import DesktopShell from "./components/DesktopShell";
import RuntimeBoundary from "./components/RuntimeBoundary";
import "./DesktopUX.css";
import "./ReleaseUX.css";
import "./OwnerWorkFeed.css";
import "./WorkbenchV4.css";
import { useLingJiConnection } from "./hooks/useLingJiConnection";
import { useReleaseMetadata } from "./hooks/useReleaseMetadata";
import { NAVIGATION } from "./navigation";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import type { PageId } from "./types";

export default function App() {
  const [page, setPage] = useState<PageId>("overview");
  const [inspectorTarget, setInspectorTarget] = useState<CaptureInspectorTarget | null>(null);
  const connection = useLingJiConnection();
  const release = useReleaseMetadata();
  const current = NAVIGATION.find((item) => item.id === page) ?? NAVIGATION[0];

  const openInspector = (target: CaptureInspectorTarget) => {
    setInspectorTarget(target);
    setPage("memory_inspector");
  };

  return (
    <DesktopShell
      api={connection.api}
      page={page}
      current={current}
      connected={connection.connected}
      connectionState={connection.state}
      releaseMetadata={release.metadata}
      runtimeStatus={connection.runtimeStatus}
      bootstrapStatus={connection.bootstrapStatus}
      runtimeBusy={connection.runtimeBusy}
      ownerStopped={connection.ownerStopped}
      autoRecoveryActive={connection.autoRecoveryActive}
      onNavigate={setPage}
      onRetry={() => void connection.connect()}
      onStopRuntime={() => void connection.stopRuntime()}
      onRestartRuntime={() => void connection.restartRuntime()}
      onCopyDiagnostics={() => release.copyDiagnostics(
        connection.state,
        connection.connected,
        connection.runtimeStatus,
        connection.bootstrapStatus,
        connection.overview,
      )}
    >
      <RuntimeBoundary
        state={connection.state}
        connected={connection.connected}
        ownerStopped={connection.ownerStopped}
        runtimeBusy={connection.runtimeBusy}
        error={connection.error}
        runtimeStatus={connection.runtimeStatus}
        bootstrapStatus={connection.bootstrapStatus}
        onConfigure={connection.configureRuntime}
        onResume={() => void connection.connect()}
      >
        <AppPages
          page={page}
          api={connection.api}
          connected={connection.connected}
          overview={connection.overview}
          inspectorTarget={inspectorTarget}
          onOpenInspector={openInspector}
          onNavigate={setPage}
        />
      </RuntimeBoundary>
    </DesktopShell>
  );
}

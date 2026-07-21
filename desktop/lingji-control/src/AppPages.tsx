import type { LingJiApi } from "./api";
import AcceptancePage from "./pages/AcceptancePage";
import BackupsPage from "./pages/BackupsPage";
import BrainStatusPage from "./pages/BrainStatusPage";
import CaptureCenterPage from "./pages/CaptureCenterPage";
import CapturePage from "./pages/CapturePage";
import JobsPage from "./pages/JobsPage";
import LogsPage from "./pages/LogsPage";
import MediaPage from "./pages/MediaPage";
import MemoryInspectorPage from "./pages/MemoryInspectorPage";
import ModelsPage from "./pages/ModelsPage";
import OverviewPage from "./pages/OverviewPage";
import SettingsPage from "./pages/SettingsPage";
import StoragePage from "./pages/StoragePage";
import SystemComputePage from "./pages/SystemComputePage";
import VectorCenterPage from "./pages/VectorCenterPage";
import "./pages/VectorCenterPage.css";
import type { CaptureInspectorTarget } from "./pages/captureCenterTypes";
import type { PageId, Row } from "./types";

type AppPagesProps = {
  page: PageId;
  api: LingJiApi;
  connected: boolean;
  overview: Row | null;
  refresh: () => Promise<void>;
  inspectorTarget: CaptureInspectorTarget | null;
  onOpenInspector: (target: CaptureInspectorTarget) => void;
};

export default function AppPages(props: AppPagesProps) {
  const { page, api, connected, overview, refresh, inspectorTarget, onOpenInspector } = props;
  return (
    <section className="page-content">
      {page === "overview" && <OverviewPage data={overview} refresh={refresh} />}
      {page === "brain_status" && <BrainStatusPage api={api} active={connected} />}
      {page === "memory_inspector" && (
        <MemoryInspectorPage key={JSON.stringify(inspectorTarget)} api={api} active={connected} />
      )}
      {page === "capture_center" && (
        <CaptureCenterPage api={api} active={connected} onOpenInspector={onOpenInspector} />
      )}
      {page === "vector_center" && <VectorCenterPage api={api} active={connected} />}
      {page === "system_compute" && <SystemComputePage api={api} active={connected} />}
      {page === "models" && <ModelsPage api={api} active={connected} />}
      {page === "jobs" && <JobsPage api={api} active={connected} />}
      {page === "capture" && <CapturePage api={api} active={connected} />}
      {page === "media" && <MediaPage api={api} active={connected} />}
      {page === "storage" && <StoragePage api={api} active={connected} />}
      {page === "backups" && <BackupsPage api={api} active={connected} />}
      {page === "acceptance" && <AcceptancePage api={api} active={connected} />}
      {page === "settings" && <SettingsPage api={api} active={connected} />}
      {page === "logs" && <LogsPage api={api} active={connected} />}
    </section>
  );
}

import type { LingJiApi } from "./api";
import AcceptancePage from "./pages/AcceptancePage";
import ActivityPage from "./pages/ActivityPage";
import AttentionPage from "./pages/AttentionPage";
import AutoReviewPage from "./pages/AutoReviewPage";
import BackupsPage from "./pages/BackupsPage";
import BrainStatusPage from "./pages/BrainStatusPage";
import CaptureCenterPage from "./pages/CaptureCenterPage";
import CapturePage from "./pages/CapturePage";
import CodexWorkspacePage from "./pages/CodexWorkspacePage";
import DiagnosticsPage from "./pages/DiagnosticsPage";
import JobsPage from "./pages/JobsPage";
import LogsPage from "./pages/LogsPage";
import MediaPage from "./pages/MediaPage";
import MemoryInspectorLoopPage from "./pages/MemoryInspectorLoopPage";
import MemoryReviewPage from "./pages/MemoryReviewPage";
import MemorySourcesPage from "./pages/MemorySourcesPage";
import ModelsPage from "./pages/ModelsPage";
import ObsidianLoopPage from "./pages/ObsidianLoopPage";
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
  inspectorTarget: CaptureInspectorTarget | null;
  onOpenInspector: (target: CaptureInspectorTarget) => void;
  onNavigate: (page: PageId) => void;
};

export default function AppPages(props: AppPagesProps) {
  const { page, api, connected, overview, inspectorTarget, onOpenInspector, onNavigate } = props;
  return <section className="page-content">
    {page === "overview" && <OverviewPage data={overview} api={api} active={connected} onNavigate={onNavigate} />}
    {page === "memory_sources" && <MemorySourcesPage api={api} active={connected} />}
    {page === "activity" && <ActivityPage api={api} active={connected} />}
    {page === "attention" && <AttentionPage api={api} active={connected} />}
    {page === "diagnostics" && <DiagnosticsPage onNavigate={onNavigate} />}
    {page === "brain_status" && <BrainStatusPage api={api} active={connected} />}
    {page === "memory_inspector" && <MemoryInspectorLoopPage api={api} active={connected} target={inspectorTarget} />}
    {page === "codex_workspace" && <CodexWorkspacePage api={api} active={connected} onOpenInspector={onOpenInspector} />}
    {page === "memory_review" && <MemoryReviewPage api={api} active={connected} onOpenInspector={onOpenInspector} />}
    {page === "auto_review" && <AutoReviewPage api={api} active={connected} />}
    {page === "capture_center" && <CaptureCenterPage api={api} active={connected} onOpenInspector={onOpenInspector} />}
    {page === "obsidian" && <ObsidianLoopPage api={api} active={connected} />}
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
  </section>;
}

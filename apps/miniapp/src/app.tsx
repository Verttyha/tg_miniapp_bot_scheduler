import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/app-shell";
import { ScreenHeader } from "./components/layout/screen-header";
import { useSessionState } from "./hooks/use-session-state";
import { DashboardHomePage } from "./pages/dashboard-home-page";
import { EventEditorPage } from "./pages/event-editor-page";
import { IntegrationsPage } from "./pages/integrations-page";
import { PollEditorPage } from "./pages/poll-editor-page";
import { PollPage } from "./pages/poll-page";
import { StatsPage } from "./pages/stats-page";

const LAUNCH_EYEBROW = "\u0417\u0430\u043f\u0443\u0441\u043a";
const LAUNCH_MESSAGE = "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u044e \u043c\u0438\u043d\u0438-\u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u043a Telegram...";
const OPEN_ERROR_TITLE = "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435";
const OPEN_ERROR_EYEBROW = "\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430";
const UNKNOWN_ERROR_LABEL = "\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430";

export function App() {
  const { token, session, loading, error } = useSessionState();

  if (loading) {
    return (
      <AppShell>
        <section className="empty-state">
          <ScreenHeader title="Telegram Mini App" eyebrow={LAUNCH_EYEBROW} />
          <div className="empty-card">{LAUNCH_MESSAGE}</div>
        </section>
      </AppShell>
    );
  }

  if (error || !session) {
    return (
      <AppShell>
        <section className="empty-state">
          <ScreenHeader title={OPEN_ERROR_TITLE} eyebrow={OPEN_ERROR_EYEBROW} />
          <div className="notice notice--error">{error ?? UNKNOWN_ERROR_LABEL}</div>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardHomePage token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId" element={<DashboardHomePage token={token} session={session} />} />
        <Route path="/integrations" element={<IntegrationsPage token={token} />} />
        <Route path="/workspaces/:workspaceId/events/new" element={<EventEditorPage token={token} session={session} />} />
        <Route path="/events/:eventId/edit" element={<EventEditorPage token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/polls/new" element={<PollEditorPage token={token} session={session} />} />
        <Route path="/polls/:pollId" element={<PollPage token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/stats" element={<StatsPage token={token} session={session} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

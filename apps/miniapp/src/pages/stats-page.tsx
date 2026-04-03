import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getWorkspaceStats } from "../api";
import { ScreenHeader } from "../components/layout/screen-header";
import { StatsCard } from "../components/ui/stats-card";
import type { SessionPayload, StatsSummary } from "../types";

const STATS_TEXT = {
  loadError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0443",
  eyebrow: "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430",
  title: "\u041f\u043e\u0441\u0435\u0449\u0430\u0435\u043c\u043e\u0441\u0442\u044c",
  loading: "\u0421\u043e\u0431\u0438\u0440\u0430\u044e \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0443..."
};

export function StatsPage({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const workspace = session.workspaces.find((item) => item.id === Number(workspaceId)) ?? session.workspaces[0] ?? null;
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) {
      return;
    }
    let active = true;
    (async () => {
      try {
        const data = await getWorkspaceStats(Number(workspaceId), token);
        if (active) {
          setSummary(data);
          setError(null);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : STATS_TEXT.loadError);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [token, workspaceId]);

  return (
    <section className="detail-screen">
      <ScreenHeader
        backTo={workspace ? `/workspaces/${workspace.id}` : "/"}
        eyebrow={STATS_TEXT.eyebrow}
        title={STATS_TEXT.title}
        description={workspace?.name}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {!summary ? (
        <div className="empty-card">{STATS_TEXT.loading}</div>
      ) : (
        <div className="stats-list">
          {summary.entries.map((entry) => (
            <StatsCard entry={entry} key={entry.user.id} />
          ))}
        </div>
      )}
    </section>
  );
}

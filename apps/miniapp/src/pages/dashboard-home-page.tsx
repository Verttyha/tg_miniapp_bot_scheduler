import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { getIntegrations, getWorkspaceEvents, getWorkspacePolls } from "../api";
import { EventCard } from "../components/dashboard/event-card";
import { ProviderLinkCard } from "../components/dashboard/provider-link-card";
import { WORKSPACE_STORAGE_KEY } from "../lib/constants";
import {
  capitalize,
  countPollVotes,
  formatCurrentDate,
  formatDateTime,
  translateConnectionStatus
} from "../lib/formatters";
import { isWorkspaceAdmin, parseWorkspaceId } from "../lib/workspace";
import type { CalendarConnection, EventItem, Poll, SessionPayload } from "../types";

const PROVIDERS = ["google", "yandex"] as const;

const DASHBOARD_TEXT = {
  loadWorkspaceError:
    "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435 \u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u0441\u0442\u0432\u0430",
  noChatsTitle: "\u041d\u0435\u0442 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043d\u044b\u0445 \u0447\u0430\u0442\u043e\u0432",
  noChatsBody:
    "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0431\u043e\u0442\u0430 \u0432 Telegram-\u0433\u0440\u0443\u043f\u043f\u0443, \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0432 \u0447\u0430\u0442\u0435 \u00ab\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u0441\u044f\u00bb \u0438\u043b\u0438 \u00ab\u0412\u0441\u0442\u0443\u043f\u0438\u0442\u044c\u00bb \u0438 \u0432\u0435\u0440\u043d\u0438\u0442\u0435\u0441\u044c \u0441\u044e\u0434\u0430, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435.",
  heroDescription:
    "\u0422\u0435\u043c\u043d\u0430\u044f \u043f\u0430\u043d\u0435\u043b\u044c \u0434\u043b\u044f \u0441\u043e\u0431\u044b\u0442\u0438\u0439, \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0439 \u0438 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u043d\u044b\u0445 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0439. \u0412\u0441\u0435 \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f \u0438 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0441\u043e\u0431\u0440\u0430\u043d\u044b \u043d\u0430 \u043e\u0434\u043d\u043e\u043c \u044d\u043a\u0440\u0430\u043d\u0435.",
  today: "\u0421\u0435\u0433\u043e\u0434\u043d\u044f",
  workspace: "\u0420\u0430\u0431\u043e\u0447\u0435\u0435 \u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u0441\u0442\u0432\u043e",
  members: "\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0438",
  events: "\u0421\u043e\u0431\u044b\u0442\u0438\u044f",
  calendars: "\u041a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u0438",
  createEvent: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  createPoll: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043e\u043f\u0440\u043e\u0441",
  adminOnlyBanner:
    "\u0421\u043e\u0437\u0434\u0430\u0432\u0430\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u044f \u0438 \u043e\u043f\u0440\u043e\u0441\u044b \u043c\u043e\u0433\u0443\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u044b. \u0412\u044b \u043f\u043e-\u043f\u0440\u0435\u0436\u043d\u0435\u043c\u0443 \u0432\u0438\u0434\u0438\u0442\u0435 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435, \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0438 \u0438 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u044f.",
  integrations: "\u0418\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0438",
  stats: "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430",
  activePoll: "\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u043e\u043f\u0440\u043e\u0441",
  upcomingEventsTitle: "\u0411\u043b\u0438\u0436\u0430\u0439\u0448\u0438\u0435 \u0441\u043e\u0431\u044b\u0442\u0438\u044f",
  upcomingEventsSubtitle:
    "\u0427\u0442\u043e \u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0432\u043f\u0435\u0440\u0435\u0434\u0438 \u0438 \u043a\u0442\u043e \u0443\u0436\u0435 \u0443\u0447\u0430\u0441\u0442\u0432\u0443\u0435\u0442.",
  loadingEvents:
    "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u0441\u043e\u0431\u044b\u0442\u0438\u044f \u0438 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438...",
  noEvents:
    "\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0441\u043e\u0431\u044b\u0442\u0438\u0439. \u0421\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u043f\u0435\u0440\u0432\u043e\u0435 \u0441\u043e\u0431\u044b\u0442\u0438\u0435 \u0438 \u043e\u043d\u043e \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u0432 \u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0435.",
  votingTitle: "\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0435",
  votingSubtitle:
    "\u041e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0432\u0430\u0440\u0438\u0430\u043d\u0442\u044b \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0438 \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043f\u043e \u0433\u043e\u043b\u043e\u0441\u0430\u043c.",
  loadingPolls: "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u044f...",
  deadline: "\u0414\u0435\u0434\u043b\u0430\u0439\u043d",
  voted: "\u041f\u0440\u043e\u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043b\u0438",
  votes: "\u0433\u043e\u043b\u043e\u0441\u043e\u0432",
  noOpenPolls:
    "\u0421\u0435\u0439\u0447\u0430\u0441 \u043d\u0435\u0442 \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0445 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0430\u043d\u0438\u0439 \u043f\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438.",
  syncTitle: "\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438",
  syncSubtitle:
    "\u0421\u0442\u0430\u0442\u0443\u0441 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u0435\u0439 \u0438 \u0431\u044b\u0441\u0442\u0440\u044b\u0439 \u043f\u0435\u0440\u0435\u0445\u043e\u0434 \u043a \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u043c \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f"
};

export function DashboardHomePage({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(() => {
    const routeWorkspaceId = parseWorkspaceId(workspaceId ?? null);
    if (routeWorkspaceId !== null) {
      return routeWorkspaceId;
    }

    return parseWorkspaceId(localStorage.getItem(WORKSPACE_STORAGE_KEY)) ?? session.workspaces[0]?.id ?? null;
  });
  const [events, setEvents] = useState<EventItem[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const routeWorkspaceId = parseWorkspaceId(workspaceId ?? null);
    if (routeWorkspaceId !== null) {
      setSelectedWorkspaceId(routeWorkspaceId);
    }
  }, [workspaceId]);

  const workspace =
    session.workspaces.find((item) => item.id === selectedWorkspaceId) ??
    session.workspaces[0] ??
    null;
  const workspaceDataId = workspace?.id ?? null;

  useEffect(() => {
    if (!workspaceDataId) {
      return;
    }

    localStorage.setItem(WORKSPACE_STORAGE_KEY, String(workspaceDataId));
    let active = true;
    setLoading(true);

    void getIntegrations(token)
      .then((connectionData) => {
        if (!active) {
          return;
        }
        setConnections(connectionData);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setConnections([]);
      });

    (async () => {
      try {
        const [eventData, pollData] = await Promise.all([
          getWorkspaceEvents(workspaceDataId, token),
          getWorkspacePolls(workspaceDataId, token),
        ]);
        if (!active) {
          return;
        }
        setEvents(eventData);
        setPolls(pollData);
        setError(null);
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : DASHBOARD_TEXT.loadWorkspaceError);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [token, workspaceDataId]);

  if (!session.workspaces.length) {
    return (
      <section className="empty-state">
        <header className="screen-header">
          <p className="screen-header__eyebrow">Mini App</p>
          <h1 className="screen-header__title">{DASHBOARD_TEXT.noChatsTitle}</h1>
        </header>
        <p className="empty-state__text">{DASHBOARD_TEXT.noChatsBody}</p>
      </section>
    );
  }

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  const canManageWorkspace = isWorkspaceAdmin(workspace, session.user.id);
  const upcomingEvents = [...events]
    .sort((left, right) => new Date(left.start_at).getTime() - new Date(right.start_at).getTime())
    .slice(0, 4);
  const featuredEvent = upcomingEvents[0] ?? null;
  const secondaryEvents = featuredEvent ? upcomingEvents.slice(1) : [];
  const openPolls = polls
    .filter((poll) => poll.status === "open" || poll.status === "needs_admin_resolution")
    .sort((left, right) => new Date(left.deadline_at).getTime() - new Date(right.deadline_at).getTime());
  const featuredPoll = openPolls[0] ?? null;
  const voteScale = featuredPoll ? Math.max(countPollVotes(featuredPoll), 1) : 1;
  const activeConnections = connections.filter((connection) => connection.status === "active").length;

  function handleWorkspaceChange(nextValue: string) {
    const nextWorkspaceId = Number(nextValue);
    setSelectedWorkspaceId(nextWorkspaceId);
    navigate(`/workspaces/${nextWorkspaceId}`);
  }

  return (
    <section className="home-screen home-screen--dashboard">
      <div className="dashboard-hero">
        <div className="dashboard-hero__copy">
          <p className="screen-header__eyebrow">Telegram Mini App</p>
          <h1 className="dashboard-hero__title">{workspace.name}</h1>
          <p className="dashboard-hero__description">{DASHBOARD_TEXT.heroDescription}</p>
        </div>
        <div className="dashboard-hero__controls">
          <div className="dashboard-date-card">
            <span>{DASHBOARD_TEXT.today}</span>
            <strong>{formatCurrentDate()}</strong>
          </div>
          <label className="workspace-select">
            <span className="workspace-select__label">{DASHBOARD_TEXT.workspace}</span>
            <select value={workspace.id} onChange={(event) => handleWorkspaceChange(event.target.value)}>
              {session.workspaces.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error ? <div className="notice notice--error">{error}</div> : null}

      <div className="dashboard-layout">
        <aside className="dashboard-sidebar">
          <article className="metric-card">
            <span>{DASHBOARD_TEXT.members}</span>
            <strong>{workspace.members.length}</strong>
          </article>
          <article className="metric-card">
            <span>{DASHBOARD_TEXT.events}</span>
            <strong>{events.length}</strong>
          </article>
          <article className="metric-card">
            <span>{DASHBOARD_TEXT.calendars}</span>
            <strong>{activeConnections}/2</strong>
          </article>

          {canManageWorkspace ? (
            <div className="primary-actions primary-actions--sidebar">
              <Link className="action-strip" to={`/workspaces/${workspace.id}/events/new`}>
                {DASHBOARD_TEXT.createEvent}
              </Link>
              <Link className="action-strip action-strip--ghost" to={`/workspaces/${workspace.id}/polls/new`}>
                {DASHBOARD_TEXT.createPoll}
              </Link>
            </div>
          ) : (
            <div className="status-banner status-banner--muted">{DASHBOARD_TEXT.adminOnlyBanner}</div>
          )}

          <div className="dashboard-shortcuts">
            <Link className="dashboard-shortcut" to="/integrations">
              {DASHBOARD_TEXT.integrations}
            </Link>
            <Link className="dashboard-shortcut" to={`/workspaces/${workspace.id}/stats`}>
              {DASHBOARD_TEXT.stats}
            </Link>
            {featuredPoll ? (
              <Link className="dashboard-shortcut" to={`/polls/${featuredPoll.id}`}>
                {DASHBOARD_TEXT.activePoll}
              </Link>
            ) : null}
          </div>
        </aside>

        <div className="dashboard-main">
          <section className="surface-panel surface-panel--events">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">{DASHBOARD_TEXT.upcomingEventsTitle}</h2>
                <p className="panel-subtitle">{DASHBOARD_TEXT.upcomingEventsSubtitle}</p>
              </div>
              <span className="panel-badge panel-badge--soft">{events.length}</span>
            </div>

            <div className="dashboard-events">
              {loading ? (
                <div className="empty-card empty-card--compact">{DASHBOARD_TEXT.loadingEvents}</div>
              ) : featuredEvent ? (
                <>
                  <EventCard canManageWorkspace={canManageWorkspace} event={featuredEvent} featured />
                  {secondaryEvents.length ? (
                    <div className="dashboard-events__list">
                      {secondaryEvents.map((event) => (
                        <EventCard canManageWorkspace={canManageWorkspace} event={event} key={event.id} />
                      ))}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="empty-card">{DASHBOARD_TEXT.noEvents}</div>
              )}
            </div>
          </section>

          <section className="surface-panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">{DASHBOARD_TEXT.votingTitle}</h2>
                <p className="panel-subtitle">{DASHBOARD_TEXT.votingSubtitle}</p>
              </div>
              <span className="panel-badge">{openPolls.length}</span>
            </div>

            {loading ? (
              <div className="empty-card empty-card--compact">{DASHBOARD_TEXT.loadingPolls}</div>
            ) : featuredPoll ? (
              <>
                <Link className="poll-feature" to={`/polls/${featuredPoll.id}`}>
                  <strong>{featuredPoll.title}</strong>
                  <span>{DASHBOARD_TEXT.deadline}: {formatDateTime(featuredPoll.deadline_at)}</span>
                  <span>{DASHBOARD_TEXT.voted}: {countPollVotes(featuredPoll)}</span>
                </Link>
                <div className="poll-option-list">
                  {featuredPoll.options.map((option) => (
                    <div className="poll-option" key={option.id}>
                      <div className="poll-option__row">
                        <strong>{option.label ?? `\u0412\u0430\u0440\u0438\u0430\u043d\u0442 ${option.id}`}</strong>
                        <span>{option.vote_count} {DASHBOARD_TEXT.votes}</span>
                      </div>
                      <div className="poll-option__meta">{formatDateTime(option.start_at)}</div>
                      <div className="poll-option__bar">
                        <div className="poll-option__fill" style={{ width: `${(option.vote_count / voteScale) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty-card">{DASHBOARD_TEXT.noOpenPolls}</div>
            )}
          </section>

          <section className="surface-panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">{DASHBOARD_TEXT.syncTitle}</h2>
                <p className="panel-subtitle">{DASHBOARD_TEXT.syncSubtitle}</p>
              </div>
              <span className="panel-badge">{activeConnections}/2</span>
            </div>

            <div className="summary-list">
              {PROVIDERS.map((provider) => {
                const connection = connections.find((item) => item.provider === provider);
                return (
                  <div className="summary-item" key={provider}>
                    <strong>{capitalize(provider)}</strong>
                    <span>{translateConnectionStatus(connection?.status ?? "pending")}</span>
                  </div>
                );
              })}
            </div>

            <div className="provider-grid provider-grid--dashboard">
              {PROVIDERS.map((provider) => {
                const connection = connections.find((item) => item.provider === provider);
                return (
                  <ProviderLinkCard
                    isActive={connection?.status === "active"}
                    key={provider}
                    provider={provider}
                    to="/integrations"
                  />
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import {
  bootstrapSession,
  connectProvider,
  createEvent,
  createPoll,
  getCurrentSession,
  getEvent,
  getIntegrations,
  getPoll,
  getWorkspaceEvents,
  getWorkspacePolls,
  getWorkspaceStats,
  resolvePoll,
  updateEvent,
  updateIntegration,
  voteOnPoll
} from "./api";
import { initTelegramApp } from "./telegram";
import type { CalendarConnection, EventItem, Poll, SessionPayload, StatsSummary, Workspace } from "./types";

function useSessionState() {
  const [token, setToken] = useState<string>(() => localStorage.getItem("scheduler.token") ?? "");
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const initData = await initTelegramApp();
        if (!token) {
          const payload = await bootstrapSession(initData);
          if (!active) {
            return;
          }
          localStorage.setItem("scheduler.token", payload.access_token);
          setToken(payload.access_token);
          setSession(payload);
          return;
        }
        const current = await getCurrentSession(token);
        if (!active) {
          return;
        }
        setSession({ access_token: token, user: current.user, workspaces: current.workspaces });
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to bootstrap session");
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
  }, [token]);

  return { token, session, loading, error };
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <header className="shell__header">
        <div>
          <p className="eyebrow">Telegram Scheduler</p>
          <h1>Collective planning inside Telegram</h1>
        </div>
        <nav className="shell__nav">
          <Link to="/">Dashboard</Link>
          <Link to="/integrations">Integrations</Link>
        </nav>
      </header>
      <main className="shell__body">{children}</main>
    </div>
  );
}

function DashboardPage({ session }: { session: SessionPayload }) {
  if (!session.workspaces.length) {
    return (
      <section className="card">
        <h2>No workspaces yet</h2>
        <p>Add the bot to a Telegram group, run <code>/setup</code>, then come back here and join the workspace.</p>
      </section>
    );
  }

  return (
    <section className="stack">
      {session.workspaces.map((workspace) => (
        <article className="card" key={workspace.id}>
          <div className="card__row">
            <div>
              <p className="eyebrow">Workspace</p>
              <h2>{workspace.name}</h2>
            </div>
            <span className="pill">{workspace.members.length} members</span>
          </div>
          <p className="muted">Members join from private chat. Admins create events, polls, and attendance updates here.</p>
          <div className="card__actions">
            <Link className="button" to={`/workspaces/${workspace.id}`}>Open dashboard</Link>
            <Link className="button button--ghost" to={`/workspaces/${workspace.id}/stats`}>Stats</Link>
          </div>
        </article>
      ))}
    </section>
  );
}

function WorkspaceDashboard({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const workspace = session.workspaces.find((item) => item.id === Number(workspaceId));
  const [events, setEvents] = useState<EventItem[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace) {
      return;
    }
    let active = true;
    (async () => {
      try {
        const [eventData, pollData] = await Promise.all([
          getWorkspaceEvents(workspace.id, token),
          getWorkspacePolls(workspace.id, token)
        ]);
        if (active) {
          setEvents(eventData);
          setPolls(pollData);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load workspace");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [token, workspace]);

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  return (
    <section className="stack">
      <article className="hero">
        <div>
          <p className="eyebrow">Workspace dashboard</p>
          <h2>{workspace.name}</h2>
        </div>
        <div className="card__actions">
          <Link className="button" to={`/workspaces/${workspace.id}/events/new`}>Create event</Link>
          <Link className="button button--ghost" to={`/workspaces/${workspace.id}/polls/new`}>Create poll</Link>
        </div>
      </article>
      {error ? <div className="notice notice--error">{error}</div> : null}
      <section className="grid">
        <article className="card">
          <div className="card__row">
            <h3>Upcoming events</h3>
            <span className="pill">{events.length}</span>
          </div>
          <div className="stack compact">
            {events.map((event) => (
              <Link key={event.id} className="list-item" to={`/events/${event.id}/edit`}>
                <strong>{event.title}</strong>
                <span>{new Date(event.start_at).toLocaleString()}</span>
              </Link>
            ))}
            {!events.length ? <p className="muted">No events yet.</p> : null}
          </div>
        </article>
        <article className="card">
          <div className="card__row">
            <h3>Polls</h3>
            <span className="pill">{polls.length}</span>
          </div>
          <div className="stack compact">
            {polls.map((poll) => (
              <Link key={poll.id} className="list-item" to={`/polls/${poll.id}`}>
                <strong>{poll.title}</strong>
                <span>{poll.status}</span>
              </Link>
            ))}
            {!polls.length ? <p className="muted">No polls yet.</p> : null}
          </div>
        </article>
      </section>
    </section>
  );
}

function EventEditor({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId, eventId } = useParams();
  const navigate = useNavigate();
  const [resolvedWorkspaceId, setResolvedWorkspaceId] = useState<number | null>(
    workspaceId ? Number(workspaceId) : null
  );
  const workspace =
    session.workspaces.find((item) => item.id === resolvedWorkspaceId) ??
    (session.workspaces.length === 1 ? session.workspaces[0] : null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>(workspace?.members.map((member) => member.user.id) ?? []);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) {
      return;
    }
    let active = true;
    (async () => {
      try {
        const event = await getEvent(Number(eventId), token);
        if (active) {
          setTitle(event.title);
          setDescription(event.description ?? "");
          setLocation(event.location ?? "");
          setStartAt(event.start_at.slice(0, 16));
          setEndAt(event.end_at.slice(0, 16));
          setSelectedIds(event.participants.map((participant) => participant.user.id));
          setResolvedWorkspaceId(event.workspace_id);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load event");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [eventId, token]);

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    const payload = {
      title,
      description,
      location,
      start_at: new Date(startAt).toISOString(),
      end_at: new Date(endAt).toISOString(),
      timezone_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
      participant_ids: selectedIds
    };
    try {
      if (eventId) {
        await updateEvent(Number(eventId), payload, token);
      } else {
        await createEvent(workspace.id, payload, token);
      }
      navigate(`/workspaces/${workspace.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save event");
    }
  }

  return (
    <section className="card">
      <p className="eyebrow">Event editor</p>
      <h2>{eventId ? "Edit event" : "Create event"}</h2>
      {error ? <div className="notice notice--error">{error}</div> : null}
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label className="field">
          <span>Description</span>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
        </label>
        <label className="field">
          <span>Location</span>
          <input value={location} onChange={(e) => setLocation(e.target.value)} />
        </label>
        <div className="grid">
          <label className="field">
            <span>Start</span>
            <input type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} required />
          </label>
          <label className="field">
            <span>End</span>
            <input type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} required />
          </label>
        </div>
        <div className="chip-grid">
          {workspace.members.map((member) => {
            const checked = selectedIds.includes(member.user.id);
            return (
              <label key={member.id} className={`chip ${checked ? "chip--active" : ""}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() =>
                    setSelectedIds((current) =>
                      checked ? current.filter((id) => id !== member.user.id) : [...current, member.user.id]
                    )
                  }
                />
                {member.user.first_name || member.user.username || `User ${member.user.id}`}
              </label>
            );
          })}
        </div>
        <button className="button" type="submit">{eventId ? "Save changes" : "Create event"}</button>
      </form>
    </section>
  );
}

function PollEditor({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const workspace = session.workspaces.find((item) => item.id === Number(workspaceId));
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [deadlineAt, setDeadlineAt] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>(workspace?.members.map((member) => member.user.id) ?? []);
  const [options, setOptions] = useState([
    { label: "Option A", start_at: "", end_at: "" },
    { label: "Option B", start_at: "", end_at: "" }
  ]);
  const [error, setError] = useState<string | null>(null);

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    try {
      await createPoll(
        workspace.id,
        {
          title,
          description,
          deadline_at: new Date(deadlineAt).toISOString(),
          timezone_name: Intl.DateTimeFormat().resolvedOptions().timeZone,
          participant_ids: selectedIds,
          options: options.map((option) => ({
            label: option.label,
            start_at: new Date(option.start_at).toISOString(),
            end_at: new Date(option.end_at).toISOString()
          }))
        },
        token
      );
      navigate(`/workspaces/${workspace.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create poll");
    }
  }

  return (
    <section className="card">
      <p className="eyebrow">Voting</p>
      <h2>Create poll</h2>
      {error ? <div className="notice notice--error">{error}</div> : null}
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label className="field">
          <span>Description</span>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
        </label>
        <label className="field">
          <span>Voting deadline</span>
          <input type="datetime-local" value={deadlineAt} onChange={(e) => setDeadlineAt(e.target.value)} required />
        </label>
        <div className="chip-grid">
          {workspace.members.map((member) => {
            const checked = selectedIds.includes(member.user.id);
            return (
              <label key={member.id} className={`chip ${checked ? "chip--active" : ""}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() =>
                    setSelectedIds((current) =>
                      checked ? current.filter((id) => id !== member.user.id) : [...current, member.user.id]
                    )
                  }
                />
                {member.user.first_name || member.user.username || `User ${member.user.id}`}
              </label>
            );
          })}
        </div>
        {options.map((option, index) => (
          <div className="grid" key={index}>
            <label className="field">
              <span>Option label</span>
              <input
                value={option.label}
                onChange={(e) =>
                  setOptions((current) =>
                    current.map((item, currentIndex) =>
                      currentIndex === index ? { ...item, label: e.target.value } : item
                    )
                  )
                }
              />
            </label>
            <label className="field">
              <span>Start</span>
              <input
                type="datetime-local"
                value={option.start_at}
                onChange={(e) =>
                  setOptions((current) =>
                    current.map((item, currentIndex) =>
                      currentIndex === index ? { ...item, start_at: e.target.value } : item
                    )
                  )
                }
                required
              />
            </label>
            <label className="field">
              <span>End</span>
              <input
                type="datetime-local"
                value={option.end_at}
                onChange={(e) =>
                  setOptions((current) =>
                    current.map((item, currentIndex) =>
                      currentIndex === index ? { ...item, end_at: e.target.value } : item
                    )
                  )
                }
                required
              />
            </label>
          </div>
        ))}
        <button className="button" type="submit">Create poll</button>
      </form>
    </section>
  );
}

function PollPage({ token }: { token: string }) {
  const { pollId } = useParams();
  const [poll, setPoll] = useState<Poll | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pollId) {
      return;
    }
    let active = true;
    (async () => {
      try {
        const data = await getPoll(Number(pollId), token);
        if (active) {
          setPoll(data);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load poll");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [pollId, token]);

  async function handleVote(optionId: number) {
    if (!poll) {
      return;
    }
    try {
      setPoll(await voteOnPoll(poll.id, optionId, token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to vote");
    }
  }

  async function handleResolve() {
    if (!poll) {
      return;
    }
    try {
      setPoll(await resolvePoll(poll.id, poll.user_vote_option_id, token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to resolve poll");
    }
  }

  if (!poll) {
    return <section className="card">{error ?? "Loading poll..."}</section>;
  }

  return (
    <section className="card stack">
      <div className="card__row">
        <div>
          <p className="eyebrow">Poll detail</p>
          <h2>{poll.title}</h2>
        </div>
        <span className="pill">{poll.status}</span>
      </div>
      {poll.options.map((option) => (
        <button key={option.id} className="vote-card" type="button" onClick={() => handleVote(option.id)}>
          <strong>{option.label ?? `Option ${option.id}`}</strong>
          <span>{new Date(option.start_at).toLocaleString()}</span>
          <span>{option.vote_count} votes</span>
        </button>
      ))}
      {poll.status === "needs_admin_resolution" ? (
        <button className="button" type="button" onClick={handleResolve}>Resolve with my selected option</button>
      ) : null}
    </section>
  );
}

function IntegrationsPage({ token }: { token: string }) {
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    try {
      setConnections(await getIntegrations(token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load integrations");
    }
  }

  useEffect(() => {
    void reload();
  }, [token]);

  async function handleConnect(provider: "google" | "yandex") {
    try {
      const payload = await connectProvider(provider, token);
      window.open(payload.authorize_url, "_blank", "noopener,noreferrer");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to connect provider");
    }
  }

  async function handleCalendarChange(connectionId: number, calendarId: string, calendarName: string) {
    try {
      await updateIntegration(connectionId, { calendar_id: calendarId, calendar_name: calendarName }, token);
      await reload();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update calendar");
    }
  }

  return (
    <section className="stack">
      <article className="hero">
        <div>
          <p className="eyebrow">Integrations</p>
          <h2>Connect Google or Yandex</h2>
        </div>
        <div className="card__actions">
          <button className="button" type="button" onClick={() => handleConnect("google")}>Connect Google</button>
          <button className="button button--ghost" type="button" onClick={() => handleConnect("yandex")}>Connect Yandex</button>
        </div>
      </article>
      {error ? <div className="notice notice--error">{error}</div> : null}
      {connections.map((connection) => (
        <article className="card" key={connection.id}>
          <div className="card__row">
            <div>
              <h3>{connection.provider}</h3>
              <p className="muted">{connection.account_email ?? "Pending authorization"}</p>
            </div>
            <span className="pill">{connection.status}</span>
          </div>
          <label className="field">
            <span>Target calendar</span>
            <select
              value={connection.calendar_id ?? ""}
              onChange={(e) =>
                handleCalendarChange(
                  connection.id,
                  e.target.value,
                  connection.calendars.find((item) => item.id === e.target.value)?.name ?? ""
                )
              }
            >
              <option value="">Select calendar</option>
              {connection.calendars.map((calendar) => (
                <option key={calendar.id} value={calendar.id}>{calendar.name}</option>
              ))}
            </select>
          </label>
        </article>
      ))}
    </section>
  );
}

function StatsPage({ token }: { token: string }) {
  const { workspaceId } = useParams();
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
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load stats");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [token, workspaceId]);

  if (!summary) {
    return <section className="card">{error ?? "Loading stats..."}</section>;
  }

  return (
    <section className="stack">
      {summary.entries.map((entry) => (
        <article className="card" key={entry.user.id}>
          <div className="card__row">
            <strong>{entry.user.first_name || entry.user.username || `User ${entry.user.id}`}</strong>
            <span className="pill">{entry.attendance_rate}%</span>
          </div>
          <p className="muted">Attended: {entry.attended} | Missed: {entry.missed} | Invited: {entry.invited}</p>
        </article>
      ))}
    </section>
  );
}

export function App() {
  const { token, session, loading, error } = useSessionState();

  if (loading) {
    return <div className="loading-screen">Bootstrapping Telegram Mini App...</div>;
  }
  if (error || !session) {
    return (
      <div className="loading-screen">
        <div className="card">
          <h2>Unable to start the Mini App</h2>
          <p>{error ?? "Unknown error"}</p>
        </div>
      </div>
    );
  }

  return (
    <Shell>
      <Routes>
        <Route path="/" element={<DashboardPage session={session} />} />
        <Route path="/integrations" element={<IntegrationsPage token={token} />} />
        <Route path="/workspaces/:workspaceId" element={<WorkspaceDashboard token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/events/new" element={<EventEditor token={token} session={session} />} />
        <Route path="/events/:eventId/edit" element={<EventEditor token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/polls/new" element={<PollEditor token={token} session={session} />} />
        <Route path="/polls/:pollId" element={<PollPage token={token} />} />
        <Route path="/workspaces/:workspaceId/stats" element={<StatsPage token={token} />} />
      </Routes>
    </Shell>
  );
}

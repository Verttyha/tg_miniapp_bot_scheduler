import { FormEvent, type ReactNode, useEffect, useState } from "react";
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
import type { CalendarConnection, EventItem, Poll, SessionPayload, StatsEntry, StatsSummary, User, Workspace } from "./types";

const WORKSPACE_STORAGE_KEY = "scheduler.workspaceId";

function useSessionState() {
  const [token, setToken] = useState<string>(() => localStorage.getItem("scheduler.token") ?? "");
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;
    async function refreshSession() {
      try {
        const current = await getCurrentSession(token);
        if (!active) {
          return;
        }
        setSession({ access_token: token, user: current.user, workspaces: current.workspaces });
        setError(null);
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to refresh session");
        }
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void refreshSession();
      }
    }

    function handleFocus() {
      void refreshSession();
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleFocus);

    return () => {
      active = false;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleFocus);
    };
  }, [token]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const hasTelegramWebApp = Boolean(window.Telegram?.WebApp);
        const initData = await initTelegramApp();
        if (initData) {
          const payload = await bootstrapSession(initData);
          if (!active) {
            return;
          }
          localStorage.setItem("scheduler.token", payload.access_token);
          setToken(payload.access_token);
          setSession(payload);
          return;
        }

        if (hasTelegramWebApp) {
          localStorage.removeItem("scheduler.token");
          if (!active) {
            return;
          }
          setToken("");
          setSession(null);
          throw new Error("Telegram session not found. Reopen the Mini App from the bot menu.");
        }

        if (!token) {
          const payload = await bootstrapSession("");
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

function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <div className="app-shell__glow app-shell__glow--top" />
      <div className="app-shell__glow app-shell__glow--bottom" />
      <main className="app-shell__screen">{children}</main>
    </div>
  );
}

function ScreenHeader({
  backTo,
  eyebrow,
  title,
  description
}: {
  backTo?: string;
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <header className="screen-header">
      {backTo ? (
        <Link className="screen-header__back" to={backTo}>
          Назад
        </Link>
      ) : null}
      {eyebrow ? <p className="screen-header__eyebrow">{eyebrow}</p> : null}
      <h1 className="screen-header__title">{title}</h1>
      {description ? <p className="screen-header__description">{description}</p> : null}
    </header>
  );
}

function HomePage({ token, session }: { token: string; session: SessionPayload }) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(() => {
    if (workspaceId) {
      return Number(workspaceId);
    }
    const stored = localStorage.getItem(WORKSPACE_STORAGE_KEY);
    return stored ? Number(stored) : session.workspaces[0]?.id ?? null;
  });
  const [events, setEvents] = useState<EventItem[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (workspaceId) {
      setSelectedWorkspaceId(Number(workspaceId));
    }
  }, [workspaceId]);

  const workspace =
    session.workspaces.find((item) => item.id === selectedWorkspaceId) ??
    session.workspaces[0] ??
    null;

  useEffect(() => {
    if (!workspace) {
      return;
    }

    localStorage.setItem(WORKSPACE_STORAGE_KEY, String(workspace.id));
    let active = true;
    setLoading(true);

    (async () => {
      try {
        const [eventData, pollData, connectionData] = await Promise.all([
          getWorkspaceEvents(workspace.id, token),
          getWorkspacePolls(workspace.id, token),
          getIntegrations(token)
        ]);
        if (!active) {
          return;
        }
        setEvents(eventData);
        setPolls(pollData);
        setConnections(connectionData);
        setError(null);
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить данные пространства");
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
  }, [token, workspace]);

  if (!session.workspaces.length) {
    return (
      <section className="empty-state">
        <ScreenHeader title="Нет подключённых чатов" eyebrow="Mini App" />
        <p className="empty-state__text">
          Добавьте бота в Telegram-группу, выполните <code>/setup</code> и вернитесь сюда, чтобы начать планирование.
        </p>
      </section>
    );
  }

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  const canManageWorkspace = isWorkspaceAdmin(workspace, session.user.id);
  const sortedEvents = [...events].sort(
    (left, right) => new Date(left.start_at).getTime() - new Date(right.start_at).getTime()
  );
  const todayKey = new Date().toDateString();
  const todayEvents = sortedEvents.filter((event) => new Date(event.start_at).toDateString() === todayKey);
  const visibleEvents = (todayEvents.length ? todayEvents : sortedEvents).slice(0, 6);
  const openPolls = polls
    .filter((poll) => poll.status === "open" || poll.status === "needs_admin_resolution")
    .sort((left, right) => new Date(left.deadline_at).getTime() - new Date(right.deadline_at).getTime());
  const providers = ["google", "yandex"] as const;

  function handleWorkspaceChange(nextValue: string) {
    const nextWorkspaceId = Number(nextValue);
    setSelectedWorkspaceId(nextWorkspaceId);
    navigate(`/workspaces/${nextWorkspaceId}`);
  }

  return (
    <section className="home-screen">
      <div className="home-screen__row">
        <div className="home-screen__label-group">
          <p className="home-screen__label">Сегодня:</p>
        </div>
        <div className="home-screen__date">{formatCurrentDate()}</div>
      </div>

      <div className="home-screen__row">
        <div className="home-screen__label-group">
          <p className="home-screen__label">Выбрать чат:</p>
        </div>
        <label className="workspace-select">
          <select value={workspace.id} onChange={(event) => handleWorkspaceChange(event.target.value)}>
            {session.workspaces.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="section-heading">
        <h2>События:</h2>
        <span className="section-heading__meta">
          {todayEvents.length ? "на сегодня" : "ближайшие"} · {workspace.members.length} участников
        </span>
      </div>

      {error ? <div className="notice notice--error">{error}</div> : null}

      <div className="event-list" data-loading={loading}>
        {loading ? (
          <div className="empty-card">Загружаю события и синхронизации…</div>
        ) : visibleEvents.length ? (
          visibleEvents.map((event) =>
            canManageWorkspace ? (
              <Link className="event-card" key={event.id} to={`/events/${event.id}/edit`}>
                <div className="event-card__time">{formatTime(event.start_at)}</div>
                <div className="event-card__body">
                  <strong>{event.title}</strong>
                  <span>{formatParticipantsLabel(event.participants.length)}</span>
                  {event.description ? <p>{event.description}</p> : null}
                </div>
              </Link>
            ) : (
              <article className="event-card" key={event.id}>
                <div className="event-card__time">{formatTime(event.start_at)}</div>
                <div className="event-card__body">
                  <strong>{event.title}</strong>
                  <span>{formatParticipantsLabel(event.participants.length)}</span>
                  {event.description ? <p>{event.description}</p> : null}
                </div>
              </article>
            )
          )
        ) : (
          <div className="empty-card">Пока нет событий. Создайте первое, и оно появится здесь.</div>
        )}
      </div>

      {canManageWorkspace ? (
        <div className="primary-actions">
          <Link className="action-strip" to={`/workspaces/${workspace.id}/events/new`}>
            Создать событие
          </Link>
          <Link className="action-strip" to={`/workspaces/${workspace.id}/polls/new`}>
            Голосование событий
          </Link>
        </div>
      ) : (
        <div className="status-banner status-banner--muted">
          Создавать и менять события могут только администраторы чата. Вы можете следить за расписанием и участвовать в голосованиях.
        </div>
      )}

      <div className="home-screen__footer">
        {openPolls.length ? (
          <Link className="status-banner" to={`/polls/${openPolls[0].id}`}>
            Открыто голосование: {openPolls[0].title}
          </Link>
        ) : (
          <div className="status-banner status-banner--muted">Открытых голосований сейчас нет</div>
        )}

        <p className="connections-title">Подключены:</p>
        <div className="provider-grid">
          {providers.map((provider) => {
            const connection = connections.find((item) => item.provider === provider);
            const isConnected = connection?.status === "active";
            const providerName = provider === "google" ? "Google" : "Yandex";
            return (
              <Link
                className={`provider-card ${isConnected ? "provider-card--active" : "provider-card--inactive"}`}
                key={provider}
                to="/integrations"
              >
                <span className={`provider-card__dot provider-card__dot--${provider}`} />
                <span>{providerName}</span>
              </Link>
            );
          })}
        </div>

        <div className="home-screen__links">
          <Link to="/integrations">Интеграции</Link>
          <Link to={`/workspaces/${workspace.id}/stats`}>Статистика</Link>
        </div>
      </div>
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
  const [eventDate, setEventDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>(workspace?.members.map((member) => member.user.id) ?? []);
  const [loading, setLoading] = useState<boolean>(Boolean(eventId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace || eventId || selectedIds.length) {
      return;
    }
    setSelectedIds(workspace.members.map((member) => member.user.id));
  }, [eventId, selectedIds.length, workspace]);

  useEffect(() => {
    if (!eventId) {
      setLoading(false);
      return;
    }

    let active = true;
    (async () => {
      try {
        const event = await getEvent(Number(eventId), token);
        if (!active) {
          return;
        }
        const start = new Date(event.start_at);
        const end = new Date(event.end_at);
        setTitle(event.title);
        setDescription(event.description ?? "");
        setLocation(event.location ?? "");
        setEventDate(toDateInputValue(start));
        setStartTime(toTimeInputValue(start));
        setEndTime(toTimeInputValue(end));
        setSelectedIds(event.participants.map((participant) => participant.user.id));
        setResolvedWorkspaceId(event.workspace_id);
        setError(null);
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить событие");
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
  }, [eventId, token]);

  if (!workspace && eventId && loading) {
    return (
      <section className="editor-screen">
        <ScreenHeader title="Загрузка события" eyebrow="Форма" />
        <div className="empty-card">Загружаю данные события…</div>
      </section>
    );
  }

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  const canManageWorkspace = isWorkspaceAdmin(workspace, session.user.id);

  if (!canManageWorkspace) {
    return (
      <section className="editor-screen">
        <ScreenHeader
          backTo={`/workspaces/${workspace.id}`}
          eyebrow="Форма"
          title={eventId ? "Изменить событие" : "Создать событие"}
          description={workspace.name}
        />
        <div className="notice">Создавать и изменять события могут только администраторы чата.</div>
      </section>
    );
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    const payload = {
      title,
      description,
      location,
      start_at: buildIsoDateTime(eventDate, startTime),
      end_at: buildEventEndIso(eventDate, startTime, endTime),
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
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить событие");
    }
  }

  return (
    <section className="editor-screen">
      <ScreenHeader
        backTo={`/workspaces/${workspace.id}`}
        eyebrow="Форма"
        title={eventId ? "Изменить событие" : "Создать событие"}
        description={workspace.name}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {loading ? (
        <div className="empty-card">Загружаю данные события…</div>
      ) : (
        <form className="editor-form" onSubmit={handleSubmit}>
          <LineField label="Название">
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </LineField>

          <LineField label="Дата">
            <input type="date" value={eventDate} onChange={(event) => setEventDate(event.target.value)} required />
          </LineField>

          <LineField label="Время">
            <div className="time-fields">
              <input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
              <span>до</span>
              <input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
            </div>
          </LineField>

          <LineField label="Описание" multiline>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              placeholder="Коротко опишите встречу"
            />
          </LineField>

          <LineField label="Место">
            <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Необязательно" />
          </LineField>

          <section className="participant-section">
            <div className="participant-section__header">
              <h2>Участники:</h2>
              <span>{selectedIds.length} выбрано</span>
            </div>

            <div className="participant-list">
              {workspace.members.map((member) => {
                const checked = selectedIds.includes(member.user.id);
                return (
                  <label className="participant-item" key={member.id}>
                    <span className={`participant-item__check ${checked ? "participant-item__check--active" : ""}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setSelectedIds((current) =>
                            checked ? current.filter((id) => id !== member.user.id) : [...current, member.user.id]
                          )
                        }
                      />
                    </span>
                    <span>{getUserDisplayName(member.user)}</span>
                  </label>
                );
              })}
            </div>
          </section>

          <div className="editor-actions">
            <button className="action-pill" type="submit">
              {eventId ? "Сохранить" : "Создать"}
            </button>
            <button className="action-pill action-pill--ghost" type="button" onClick={() => navigate(`/workspaces/${workspace.id}`)}>
              Отмена
            </button>
          </div>
        </form>
      )}
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
    { label: "Вариант 1", start_at: "", end_at: "" },
    { label: "Вариант 2", start_at: "", end_at: "" }
  ]);
  const [error, setError] = useState<string | null>(null);

  if (!workspace) {
    return <Navigate to="/" replace />;
  }

  const canManageWorkspace = isWorkspaceAdmin(workspace, session.user.id);

  if (!canManageWorkspace) {
    return (
      <section className="editor-screen">
        <ScreenHeader
          backTo={`/workspaces/${workspace.id}`}
          eyebrow="Голосование"
          title="Создать опрос"
          description="Выберите несколько вариантов времени, а команда проголосует"
        />
        <div className="notice">Создавать опросы могут только администраторы чата.</div>
      </section>
    );
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
      setError(requestError instanceof Error ? requestError.message : "Не удалось создать голосование");
    }
  }

  return (
    <section className="editor-screen">
      <ScreenHeader
        backTo={`/workspaces/${workspace.id}`}
        eyebrow="Голосование"
        title="Создать опрос"
        description="Выберите несколько вариантов времени, а команда проголосует"
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      <form className="editor-form" onSubmit={handleSubmit}>
        <LineField label="Название">
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </LineField>

        <LineField label="Дедлайн">
          <input
            type="datetime-local"
            value={deadlineAt}
            onChange={(event) => setDeadlineAt(event.target.value)}
            required
          />
        </LineField>

        <LineField label="Описание" multiline>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            placeholder="Что участникам важно знать перед голосованием"
          />
        </LineField>

        <section className="participant-section">
          <div className="participant-section__header">
            <h2>Участники:</h2>
            <span>{selectedIds.length} выбрано</span>
          </div>
          <div className="participant-list">
            {workspace.members.map((member) => {
              const checked = selectedIds.includes(member.user.id);
              return (
                <label className="participant-item" key={member.id}>
                  <span className={`participant-item__check ${checked ? "participant-item__check--active" : ""}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setSelectedIds((current) =>
                          checked ? current.filter((id) => id !== member.user.id) : [...current, member.user.id]
                        )
                      }
                    />
                  </span>
                  <span>{getUserDisplayName(member.user)}</span>
                </label>
              );
            })}
          </div>
        </section>

        <section className="options-section">
          <div className="participant-section__header">
            <h2>Варианты:</h2>
            <button
              className="text-link"
              type="button"
              onClick={() =>
                setOptions((current) => [...current, { label: `Вариант ${current.length + 1}`, start_at: "", end_at: "" }])
              }
            >
              Добавить
            </button>
          </div>
          <div className="options-list">
            {options.map((option, index) => (
              <article className="option-card" key={index}>
                <label className="field-stack">
                  <span>Название</span>
                  <input
                    value={option.label}
                    onChange={(event) =>
                      setOptions((current) =>
                        current.map((item, currentIndex) =>
                          currentIndex === index ? { ...item, label: event.target.value } : item
                        )
                      )
                    }
                    required
                  />
                </label>
                <label className="field-stack">
                  <span>Начало</span>
                  <input
                    type="datetime-local"
                    value={option.start_at}
                    onChange={(event) =>
                      setOptions((current) =>
                        current.map((item, currentIndex) =>
                          currentIndex === index ? { ...item, start_at: event.target.value } : item
                        )
                      )
                    }
                    required
                  />
                </label>
                <label className="field-stack">
                  <span>Конец</span>
                  <input
                    type="datetime-local"
                    value={option.end_at}
                    onChange={(event) =>
                      setOptions((current) =>
                        current.map((item, currentIndex) =>
                          currentIndex === index ? { ...item, end_at: event.target.value } : item
                        )
                      )
                    }
                    required
                  />
                </label>
              </article>
            ))}
          </div>
        </section>

        <div className="editor-actions">
          <button className="action-pill" type="submit">
            Создать
          </button>
          <button className="action-pill action-pill--ghost" type="button" onClick={() => navigate(`/workspaces/${workspace.id}`)}>
            Отмена
          </button>
        </div>
      </form>
    </section>
  );
}

function PollPage({ token, session }: { token: string; session: SessionPayload }) {
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
          setError(null);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить голосование");
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
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить голос");
    }
  }

  async function handleResolve() {
    if (!poll) {
      return;
    }
    try {
      setPoll(await resolvePoll(poll.id, poll.user_vote_option_id, token));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось завершить голосование");
    }
  }

  const workspace = poll
    ? session.workspaces.find((item) => item.id === poll.workspace_id) ?? session.workspaces[0] ?? null
    : session.workspaces[0] ?? null;
  const canManageWorkspace = workspace ? isWorkspaceAdmin(workspace, session.user.id) : false;
  const voteInChatOnly = Boolean(poll?.has_chat_poll && poll.status === "open");

  return (
    <section className="detail-screen">
      <ScreenHeader
        backTo={workspace ? `/workspaces/${workspace.id}` : "/"}
        eyebrow="Голосование"
        title={poll?.title ?? "Загрузка голосования"}
        description={poll ? `Статус: ${translatePollStatus(poll.status)}` : undefined}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {!poll ? (
        <div className="empty-card">Подгружаю варианты…</div>
      ) : (
        <>
          <div className="status-banner">
            Дедлайн: {formatDateTime(poll.deadline_at)} · проголосовали {countPollVotes(poll)}
          </div>
          {voteInChatOnly ? (
            <div className="status-banner status-banner--muted">
              Голосование идёт в Telegram-чате. Бот сам считает ответы и закроет poll в момент дедлайна.
            </div>
          ) : null}
          <div className="vote-list">
            {poll.options.map((option) => {
              const selected = poll.user_vote_option_id === option.id;
              const className = `vote-card ${selected ? "vote-card--selected" : ""} ${voteInChatOnly ? "vote-card--readonly" : ""}`;
              if (voteInChatOnly) {
                return (
                  <article className={className} key={option.id}>
                    <strong>{option.label ?? `Вариант ${option.id}`}</strong>
                    <span>{formatDateTime(option.start_at)}</span>
                    <span>{option.vote_count} голосов</span>
                  </article>
                );
              }
              return (
                <button
                  className={className}
                  key={option.id}
                  type="button"
                  onClick={() => handleVote(option.id)}
                >
                  <strong>{option.label ?? `Вариант ${option.id}`}</strong>
                  <span>{formatDateTime(option.start_at)}</span>
                  <span>{option.vote_count} голосов</span>
                </button>
              );
            })}
          </div>
          {poll.status === "needs_admin_resolution" ? (
            canManageWorkspace ? (
              <button className="action-pill action-pill--full" type="button" onClick={handleResolve}>
              Завершить голосование выбранным вариантом
            </button>
            ) : (
              <div className="status-banner status-banner--muted">
                Завершить голосование может только администратор чата.
              </div>
            )
          ) : null}
        </>
      )}
    </section>
  );
}

function IntegrationsPage({ token }: { token: string }) {
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function reload() {
    try {
      setLoading(true);
      setConnections(await getIntegrations(token));
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить интеграции");
    } finally {
      setLoading(false);
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
      setError(requestError instanceof Error ? requestError.message : "Не удалось открыть подключение");
    }
  }

  async function handleCalendarChange(connectionId: number, calendarId: string, calendarName: string) {
    try {
      await updateIntegration(connectionId, { calendar_id: calendarId, calendar_name: calendarName }, token);
      await reload();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось обновить календарь");
    }
  }

  return (
    <section className="detail-screen">
      <ScreenHeader
        backTo="/"
        eyebrow="Синхронизации"
        title="Календари"
        description="Подключите Google Calendar и Yandex Calendar, чтобы события синхронизировались автоматически"
      />

      <div className="editor-actions">
        <button className="action-pill" type="button" onClick={() => handleConnect("google")}>
          Google
        </button>
        <button className="action-pill action-pill--ghost" type="button" onClick={() => handleConnect("yandex")}>
          Yandex
        </button>
      </div>

      {error ? <div className="notice notice--error">{error}</div> : null}

      {loading ? <div className="empty-card">Загружаю подключения…</div> : null}

      <div className="integrations-list">
        {connections.map((connection) => (
          <article className="integration-card" key={connection.id}>
            <div className="integration-card__header">
              <div>
                <h2>{capitalize(connection.provider)}</h2>
                <p>{connection.account_email ?? "Авторизация ещё не завершена"}</p>
              </div>
              <span className={`integration-status integration-status--${connection.status}`}>
                {translateConnectionStatus(connection.status)}
              </span>
            </div>

            <label className="field-stack">
              <span>Календарь для записи событий</span>
              <select
                value={connection.calendar_id ?? ""}
                onChange={(event) =>
                  handleCalendarChange(
                    connection.id,
                    event.target.value,
                    connection.calendars.find((item) => item.id === event.target.value)?.name ?? ""
                  )
                }
              >
                <option value="">Выберите календарь</option>
                {connection.calendars.map((calendar) => (
                  <option key={calendar.id} value={calendar.id}>
                    {calendar.name}
                  </option>
                ))}
              </select>
            </label>
          </article>
        ))}
      </div>
    </section>
  );
}

function StatsPage({ token, session }: { token: string; session: SessionPayload }) {
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
          setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить статистику");
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
        eyebrow="Статистика"
        title="Посещаемость"
        description={workspace?.name}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {!summary ? (
        <div className="empty-card">Собираю статистику…</div>
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

function StatsCard({ entry }: { entry: StatsEntry }) {
  return (
    <article className="stats-card">
      <div className="stats-card__header">
        <strong>{getUserDisplayName(entry.user)}</strong>
        <span>{entry.attendance_rate}%</span>
      </div>
      <div className="stats-card__bar">
        <div className="stats-card__fill" style={{ width: `${entry.attendance_rate}%` }} />
      </div>
      <p>
        Посетил: {entry.attended} · Пропустил: {entry.missed} · Приглашён: {entry.invited}
      </p>
    </article>
  );
}

function LineField({
  label,
  children,
  multiline = false
}: {
  label: string;
  children: ReactNode;
  multiline?: boolean;
}) {
  return (
    <label className={`line-field ${multiline ? "line-field--multiline" : ""}`}>
      <span>{label}:</span>
      <div className="line-field__control">{children}</div>
    </label>
  );
}

export function App() {
  const { token, session, loading, error } = useSessionState();

  if (loading) {
    return (
      <AppShell>
        <section className="empty-state">
          <ScreenHeader title="Telegram Mini App" eyebrow="Запуск" />
          <div className="empty-card">Подключаю мини-приложение к Telegram…</div>
        </section>
      </AppShell>
    );
  }

  if (error || !session) {
    return (
      <AppShell>
        <section className="empty-state">
          <ScreenHeader title="Не удалось открыть приложение" eyebrow="Ошибка запуска" />
          <div className="notice notice--error">{error ?? "Неизвестная ошибка"}</div>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId" element={<HomePage token={token} session={session} />} />
        <Route path="/integrations" element={<IntegrationsPage token={token} />} />
        <Route path="/workspaces/:workspaceId/events/new" element={<EventEditor token={token} session={session} />} />
        <Route path="/events/:eventId/edit" element={<EventEditor token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/polls/new" element={<PollEditor token={token} session={session} />} />
        <Route path="/polls/:pollId" element={<PollPage token={token} session={session} />} />
        <Route path="/workspaces/:workspaceId/stats" element={<StatsPage token={token} session={session} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

function buildIsoDateTime(dateValue: string, timeValue: string) {
  return new Date(`${dateValue}T${timeValue}`).toISOString();
}

function buildEventEndIso(dateValue: string, startTimeValue: string, endTimeValue: string) {
  const start = new Date(`${dateValue}T${startTimeValue}`);
  if (endTimeValue) {
    const end = new Date(`${dateValue}T${endTimeValue}`);
    if (end.getTime() > start.getTime()) {
      return end.toISOString();
    }
  }

  const fallback = new Date(start);
  fallback.setHours(fallback.getHours() + 1);
  return fallback.toISOString();
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toTimeInputValue(date: Date) {
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function formatCurrentDate() {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" }).format(new Date());
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleString("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatParticipantsLabel(count: number) {
  if (count % 10 === 1 && count % 100 !== 11) {
    return `Участник: ${count}`;
  }
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
    return `Участника: ${count}`;
  }
  return `Участников: ${count}`;
}

function countPollVotes(poll: Poll) {
  return Object.values(poll.vote_totals).reduce((total, value) => total + value, 0);
}

function getUserDisplayName(user: User) {
  return user.first_name || user.username || `User ${user.id}`;
}

function translatePollStatus(status: string) {
  switch (status) {
    case "open":
      return "открыто";
    case "needs_admin_resolution":
      return "нужно решение администратора";
    case "finalized":
      return "завершено";
    default:
      return status;
  }
}

function translateConnectionStatus(status: string) {
  switch (status) {
    case "active":
      return "Подключён";
    case "pending":
      return "Ожидает";
    default:
      return status;
  }
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getWorkspaceMembership(workspace: Workspace, userId: number) {
  return workspace.members.find((member) => member.user.id === userId) ?? null;
}

function isWorkspaceAdmin(workspace: Workspace, userId: number) {
  const membership = getWorkspaceMembership(workspace, userId);
  return membership?.role === "owner" || membership?.role === "admin";
}

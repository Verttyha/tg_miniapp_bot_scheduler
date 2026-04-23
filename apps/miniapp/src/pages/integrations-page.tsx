import { useEffect, useRef, useState } from "react";
import { connectProvider, getIntegrations, updateIntegration } from "../api";
import { ScreenHeader } from "../components/layout/screen-header";
import { capitalize, translateConnectionStatus } from "../lib/formatters";
import type { CalendarConnection } from "../types";

const INTEGRATIONS_TEXT = {
  loadError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0438",
  connectError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435",
  updateError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c",
  eyebrow: "\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438",
  title: "\u041a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u0438",
  description:
    "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0435 Google Calendar \u0438 Yandex Calendar, \u0447\u0442\u043e\u0431\u044b \u0441\u043e\u0431\u044b\u0442\u0438\u044f \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043b\u0438\u0441\u044c \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438",
  loading: "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f...",
  refreshing: "\u041e\u0431\u043d\u043e\u0432\u043b\u044f\u044e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f...",
  pendingAuth: "\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f \u0435\u0449\u0435 \u043d\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430",
  yandexDisabled: "Yandex временно отключен",
  calendarLabel: "\u041a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c \u0434\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0438 \u0441\u043e\u0431\u044b\u0442\u0438\u0439",
  chooseCalendar: "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c"
};

export function IntegrationsPage({ token }: { token: string }) {
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const requestSeq = useRef(0);
  const hasLoadedOnce = useRef(false);

  async function reload() {
    requestSeq.current += 1;
    const requestId = requestSeq.current;
    try {
      if (!hasLoadedOnce.current) {
        setInitialLoading(true);
      } else {
        setRefreshing(true);
      }
      const data = await getIntegrations(token);
      if (requestId !== requestSeq.current) {
        return;
      }
      setConnections(data);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : INTEGRATIONS_TEXT.loadError);
    } finally {
      hasLoadedOnce.current = true;
      setInitialLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void reload();
  }, [token]);

  async function handleConnect(provider: "google" | "yandex") {
    if (provider === "yandex") {
      return;
    }
    try {
      const payload = await connectProvider(provider, token);
      window.open(payload.authorize_url, "_blank", "noopener,noreferrer");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : INTEGRATIONS_TEXT.connectError);
    }
  }

  async function handleCalendarChange(connectionId: number, calendarId: string, calendarName: string) {
    try {
      await updateIntegration(connectionId, { calendar_id: calendarId, calendar_name: calendarName }, token);
      await reload();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : INTEGRATIONS_TEXT.updateError);
    }
  }

  const googleConnection = connections.find((connection) => connection.provider === "google");
  const googleActive = googleConnection?.status === "active";

  return (
    <section className="detail-screen">
      <ScreenHeader
        backTo="/"
        eyebrow={INTEGRATIONS_TEXT.eyebrow}
        title={INTEGRATIONS_TEXT.title}
        description={INTEGRATIONS_TEXT.description}
      />

      <div className="editor-actions">
        <button
          className={`action-pill ${googleActive ? "action-pill--google-active" : "action-pill--google-inactive"}`}
          type="button"
          onClick={() => handleConnect("google")}
        >
          {googleActive ? "Google подключен" : "Подключить Google"}
        </button>
        <button className="action-pill action-pill--ghost" type="button" disabled>
          {INTEGRATIONS_TEXT.yandexDisabled}
        </button>
      </div>

      {error ? <div className="notice notice--error">{error}</div> : null}
      {refreshing ? <div className="status-banner status-banner--muted">{INTEGRATIONS_TEXT.refreshing}</div> : null}

      {initialLoading ? <div className="empty-card">{INTEGRATIONS_TEXT.loading}</div> : null}

      <div className="integrations-list">
        {connections.map((connection) => (
          <article className="integration-card" key={connection.id}>
            <div className="integration-card__header">
              <div>
                <h2>{capitalize(connection.provider)}</h2>
                <p>{connection.account_email ?? INTEGRATIONS_TEXT.pendingAuth}</p>
              </div>
              <span className={`integration-status integration-status--${connection.status}`}>
                {translateConnectionStatus(connection.status)}
              </span>
            </div>

            <label className="field-stack">
              <span>{INTEGRATIONS_TEXT.calendarLabel}</span>
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
                <option value="">{INTEGRATIONS_TEXT.chooseCalendar}</option>
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

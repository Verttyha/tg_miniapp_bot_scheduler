import type { CalendarConnection, EventItem, ExternalCalendarEvent, Poll, SessionPayload, Workspace } from "./types";

const API_BASE = "/api";

const ERROR_TRANSLATIONS: Record<string, string> = {
  "Admin access required": "Требуются права администратора",
  "Calendar connection not found": "Подключение календаря не найдено",
  "Cancelled event cannot be completed": "Отмененное событие нельзя завершить",
  "Event not found": "Событие не найдено",
  "Google integration is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.":
    "Интеграция Google не настроена. Укажите GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET.",
  "Participant is not in workspace": "Участник не входит в это рабочее пространство",
  "Poll not found": "Голосование не найдено",
  "Poll option not found": "Вариант голосования не найден",
  "Selected poll option not found": "Выбранный вариант голосования не найден",
  "Telegram bot is not configured to close chat polls": "Бот Telegram не настроен для закрытия голосований в чате",
  "Telegram bot is not configured to publish chat polls": "Бот Telegram не настроен для публикации голосований в чате",
  "Telegram did not return poll details for the created chat poll":
    "Telegram не вернул данные созданного голосования",
  "Unknown calendar provider": "Неизвестный провайдер календаря",
  "User is not included in this poll": "Пользователь не добавлен в это голосование",
  "Vote in the Telegram chat poll": "Голосуйте в опросе Telegram-чата",
  "Voting is closed": "Голосование закрыто",
  "Workspace not found": "Рабочее пространство не найдено",
  "Workspace not found for current user": "Рабочее пространство недоступно текущему пользователю",
  "end_at must be greater than start_at": "Время окончания должно быть позже времени начала",
  "Unexpected request failure": "Неожиданная ошибка запроса"
};

function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function translateErrorMessage(message: string): string {
  const participantMatch = message.match(/^Participant (\d+) is not in workspace$/);
  if (participantMatch) {
    return `Участник ${participantMatch[1]} не входит в это рабочее пространство`;
  }
  if (message.startsWith("Unable to publish Telegram poll to the chat:")) {
    return "Не удалось опубликовать голосование в Telegram-чате";
  }
  return ERROR_TRANSLATIONS[message] ?? message;
}

function extractErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    return translateErrorMessage(detail);
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return translateErrorMessage(item.msg);
        }
        return null;
      })
      .filter(Boolean);
    if (messages.length) {
      return messages.join("; ");
    }
  }
  return translateErrorMessage(fallback);
}

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(extractErrorMessage(payload.detail, "Unexpected request failure"));
  }
  return (await response.json()) as T;
}

export async function bootstrapSession(initData: string): Promise<SessionPayload> {
  return request<SessionPayload>("/auth/telegram/init-data", {
    method: "POST",
    body: JSON.stringify({ init_data: initData || null })
  });
}

export async function getCurrentSession(token: string): Promise<{ user: SessionPayload["user"]; workspaces: Workspace[] }> {
  return request<{ user: SessionPayload["user"]; workspaces: Workspace[] }>("/me", undefined, token);
}

export async function getWorkspaceEvents(workspaceId: number, token: string): Promise<EventItem[]> {
  return request<EventItem[]>(`/workspaces/${workspaceId}/events`, undefined, token);
}

export async function getEvent(eventId: number, token: string): Promise<EventItem> {
  return request<EventItem>(`/events/${eventId}`, undefined, token);
}

export async function createEvent(workspaceId: number, payload: Record<string, unknown>, token: string): Promise<EventItem> {
  return request<EventItem>(`/workspaces/${workspaceId}/events`, {
    method: "POST",
    body: JSON.stringify(payload)
  }, token);
}

export async function updateEvent(eventId: number, payload: Record<string, unknown>, token: string): Promise<EventItem> {
  return request<EventItem>(`/events/${eventId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  }, token);
}

export async function deleteEvent(eventId: number, token: string): Promise<EventItem> {
  return request<EventItem>(`/events/${eventId}`, { method: "DELETE" }, token);
}

export async function completeEvent(eventId: number, token: string): Promise<EventItem> {
  return request<EventItem>(`/events/${eventId}/complete`, { method: "POST" }, token);
}

export async function getWorkspacePolls(workspaceId: number, token: string): Promise<Poll[]> {
  return request<Poll[]>(`/workspaces/${workspaceId}/polls`, undefined, token);
}

export async function createPoll(workspaceId: number, payload: Record<string, unknown>, token: string): Promise<Poll> {
  return request<Poll>(`/workspaces/${workspaceId}/polls`, {
    method: "POST",
    body: JSON.stringify(payload)
  }, token);
}

export async function getPoll(pollId: number, token: string): Promise<Poll> {
  return request<Poll>(`/polls/${pollId}`, undefined, token);
}

export async function deletePoll(pollId: number, token: string): Promise<Poll> {
  return request<Poll>(`/polls/${pollId}`, { method: "DELETE" }, token);
}

export async function voteOnPoll(pollId: number, optionId: number, token: string): Promise<Poll> {
  return request<Poll>(`/polls/${pollId}/vote`, {
    method: "POST",
    body: JSON.stringify({ option_id: optionId })
  }, token);
}

export async function resolvePoll(pollId: number, optionId: number | null, token: string): Promise<Poll> {
  return request<Poll>(`/polls/${pollId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ selected_option_id: optionId })
  }, token);
}

export async function getIntegrations(token: string): Promise<CalendarConnection[]> {
  return request<CalendarConnection[]>("/integrations", undefined, token);
}

export async function getGoogleCalendarEvents(token: string): Promise<ExternalCalendarEvent[]> {
  return request<ExternalCalendarEvent[]>("/integrations/google/events", undefined, token);
}

export async function connectProvider(provider: "google" | "yandex", token: string): Promise<{ authorize_url: string }> {
  return request<{ authorize_url: string }>(`/integrations/${provider}/connect`, { method: "POST" }, token);
}

export async function updateIntegration(connectionId: number, payload: Record<string, unknown>, token: string): Promise<CalendarConnection> {
  return request<CalendarConnection>(`/integrations/${connectionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  }, token);
}

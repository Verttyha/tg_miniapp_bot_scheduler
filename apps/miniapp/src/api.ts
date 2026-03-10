import type { CalendarConnection, EventItem, Poll, SessionPayload, StatsSummary, Workspace } from "./types";

const API_BASE = "/api";

function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
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
    throw new Error(payload.detail ?? "Unexpected request failure");
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

export async function connectProvider(provider: "google" | "yandex", token: string): Promise<{ authorize_url: string }> {
  return request<{ authorize_url: string }>(`/integrations/${provider}/connect`, { method: "POST" }, token);
}

export async function updateIntegration(connectionId: number, payload: Record<string, unknown>, token: string): Promise<CalendarConnection> {
  return request<CalendarConnection>(`/integrations/${connectionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  }, token);
}

export async function getWorkspaceStats(workspaceId: number, token: string): Promise<StatsSummary> {
  return request<StatsSummary>(`/workspaces/${workspaceId}/stats`, undefined, token);
}

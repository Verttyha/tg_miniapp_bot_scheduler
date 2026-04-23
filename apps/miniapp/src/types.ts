export interface User {
  id: number;
  telegram_user_id: number | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string | null;
}

export interface WorkspaceMember {
  id: number;
  role: string;
  joined_at: string;
  user: User;
}

export interface Workspace {
  id: number;
  name: string;
  telegram_chat_id: number | null;
  owner_user_id: number;
  created_at: string;
  members: WorkspaceMember[];
}

export interface EventParticipant {
  id: number;
  attendance_status: string;
  user: User;
}

export interface EventItem {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  location: string | null;
  start_at: string;
  end_at: string;
  timezone_name: string;
  status: string;
  source: string;
  created_at: string;
  participants: EventParticipant[];
}

export interface PollOption {
  id: number;
  label: string | null;
  start_at: string;
  end_at: string;
  vote_count: number;
}

export interface Poll {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  timezone_name: string;
  deadline_at: string;
  status: string;
  selected_option_id: number | null;
  resulting_event_id: number | null;
  participant_ids: number[];
  options: PollOption[];
  vote_totals: Record<number, number>;
  user_vote_option_id: number | null;
  has_chat_poll: boolean;
}

export interface CalendarOption {
  id: string;
  name: string;
}

export interface CalendarConnection {
  id: number;
  provider: string;
  status: string;
  account_email: string | null;
  calendar_id: string | null;
  calendar_name: string | null;
  token_expires_at: string | null;
  provider_metadata: Record<string, unknown> | null;
  calendars: CalendarOption[];
}

export interface StatsEntry {
  user: User;
  attended: number;
  missed: number;
  invited: number;
  attendance_rate: number;
}

export interface StatsSummary {
  workspace_id: number;
  generated_at: string;
  entries: StatsEntry[];
}

export interface SessionPayload {
  access_token: string;
  user: User;
  workspaces: Workspace[];
}

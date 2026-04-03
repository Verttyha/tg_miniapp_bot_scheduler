import type { Poll, User } from "../types";

const EVENT_LABELS = {
  one: "\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a",
  few: "\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430",
  many: "\u0423\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432"
};

const POLL_STATUS = {
  open: "\u043e\u0442\u043a\u0440\u044b\u0442\u043e",
  needs_admin_resolution: "\u043d\u0443\u0436\u043d\u043e \u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430",
  finalized: "\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e"
};

const CONNECTION_STATUS = {
  active: "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d",
  pending: "\u041e\u0436\u0438\u0434\u0430\u0435\u0442"
};

const EVENT_STATUS = {
  scheduled: "\u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u043e",
  cancelled: "\u043e\u0442\u043c\u0435\u043d\u0435\u043d\u043e",
  draft: "\u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a"
};

export function formatCurrentDate() {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" }).format(new Date());
}

export function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export function formatEventDay(dateString: string) {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(new Date(dateString));
}

export function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleString("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function formatParticipantsLabel(count: number) {
  if (count % 10 === 1 && count % 100 !== 11) {
    return `${EVENT_LABELS.one}: ${count}`;
  }
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
    return `${EVENT_LABELS.few}: ${count}`;
  }
  return `${EVENT_LABELS.many}: ${count}`;
}

export function countPollVotes(poll: Poll) {
  return Object.values(poll.vote_totals).reduce((total, value) => total + value, 0);
}

export function getUserDisplayName(user: User) {
  return user.first_name || user.username || `User ${user.id}`;
}

export function translatePollStatus(status: string) {
  switch (status) {
    case "open":
      return POLL_STATUS.open;
    case "needs_admin_resolution":
      return POLL_STATUS.needs_admin_resolution;
    case "finalized":
      return POLL_STATUS.finalized;
    default:
      return status;
  }
}

export function translateConnectionStatus(status: string) {
  switch (status) {
    case "active":
      return CONNECTION_STATUS.active;
    case "pending":
      return CONNECTION_STATUS.pending;
    default:
      return status;
  }
}

export function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function translateEventStatus(status: string) {
  switch (status) {
    case "scheduled":
      return EVENT_STATUS.scheduled;
    case "cancelled":
      return EVENT_STATUS.cancelled;
    case "draft":
      return EVENT_STATUS.draft;
    default:
      return status;
  }
}

import { Link } from "react-router-dom";
import {
  formatEventDay,
  formatParticipantsLabel,
  formatTime,
  translateEventStatus
} from "../../lib/formatters";
import type { EventItem } from "../../types";

interface EventCardProps {
  event: EventItem;
  canManageWorkspace: boolean;
  featured?: boolean;
}

export function EventCard({ event, canManageWorkspace, featured = false }: EventCardProps) {
  const content = (
    <>
      <div className="event-card__time-block">
        <div className="event-card__time">{formatTime(event.start_at)}</div>
        <span className="event-card__date">{formatEventDay(event.start_at)}</span>
      </div>
      <div className="event-card__body">
        <strong>{event.title}</strong>
        <span>{event.location ?? formatParticipantsLabel(event.participants.length)}</span>
        {event.description ? <p>{event.description}</p> : null}
      </div>
      <div className="event-card__aside">
        <span className="event-card__pill">{formatParticipantsLabel(event.participants.length)}</span>
        <span className="event-card__status">{translateEventStatus(event.status)}</span>
      </div>
    </>
  );
  const className = `event-card ${featured ? "event-card--featured" : ""}`.trim();

  if (canManageWorkspace) {
    return (
      <Link className={className} to={`/events/${event.id}/edit`}>
        {content}
      </Link>
    );
  }

  return <article className={className}>{content}</article>;
}

import { useId, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  formatEventDay,
  getUserDisplayName,
  formatParticipantsLabel,
  formatTime,
  translateEventStatus
} from "../../lib/formatters";
import type { EventItem } from "../../types";

interface EventCardProps {
  event: EventItem;
  canManageWorkspace: boolean;
  featured?: boolean;
  defaultParticipantsExpanded?: boolean;
}

export function EventCard({
  event,
  canManageWorkspace,
  featured = false,
  defaultParticipantsExpanded = false,
}: EventCardProps) {
  const [showParticipants, setShowParticipants] = useState(defaultParticipantsExpanded);
  const participantsId = useId();
  const participantNames = useMemo(
    () => event.participants.map((participant) => getUserDisplayName(participant.user)),
    [event.participants]
  );

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
  const toggleLabel = showParticipants ? "Скрыть участников" : "Показать участников";

  return (
    <article className={className}>
      {canManageWorkspace ? (
        <Link className="event-card__main" to={`/events/${event.id}/edit`}>
          {content}
        </Link>
      ) : (
        <div className="event-card__main">{content}</div>
      )}
      <button
        aria-controls={participantsId}
        aria-expanded={showParticipants}
        className="event-card__participants-toggle"
        onClick={() => setShowParticipants((value) => !value)}
        type="button"
      >
        {toggleLabel}
      </button>
      {showParticipants ? (
        <ul className="event-card__participants-list" id={participantsId}>
          {participantNames.map((name, index) => (
            <li key={`${name}-${index}`}>{name}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

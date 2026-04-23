import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { createEvent, deleteEvent, getEvent, updateEvent } from "../api";
import { ParticipantSelector } from "../components/forms/participant-selector";
import { ScreenHeader } from "../components/layout/screen-header";
import { LineField } from "../components/ui/line-field";
import { buildEventEndIso, buildIsoDateTime, toDateInputValue, toTimeInputValue } from "../lib/date";
import { isWorkspaceAdmin } from "../lib/workspace";
import type { SessionPayload } from "../types";

const EVENT_EDITOR_TEXT = {
  loadError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  loadTitle: "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0441\u043e\u0431\u044b\u0442\u0438\u044f",
  formEyebrow: "\u0424\u043e\u0440\u043c\u0430",
  loadMessage: "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u044e \u0434\u0430\u043d\u043d\u044b\u0435 \u0441\u043e\u0431\u044b\u0442\u0438\u044f...",
  editTitle: "\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  createTitle: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  adminOnly:
    "\u0421\u043e\u0437\u0434\u0430\u0432\u0430\u0442\u044c \u0438 \u0438\u0437\u043c\u0435\u043d\u044f\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u044f \u043c\u043e\u0433\u0443\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u044b \u0447\u0430\u0442\u0430.",
  saveError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  deleteError: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435",
  noParticipants: "\u041d\u0435\u043b\u044c\u0437\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435 \u0431\u0435\u0437 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432",
  invalidEventTime: "\u0412\u0440\u0435\u043c\u044f \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043f\u043e\u0437\u0436\u0435 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u043d\u0430\u0447\u0430\u043b\u0430",
  titleLabel: "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
  dateLabel: "\u0414\u0430\u0442\u0430",
  timeLabel: "\u0412\u0440\u0435\u043c\u044f",
  untilLabel: "\u0434\u043e",
  descriptionLabel: "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435",
  descriptionPlaceholder: "\u041a\u043e\u0440\u043e\u0442\u043a\u043e \u043e\u043f\u0438\u0448\u0438\u0442\u0435 \u0432\u0441\u0442\u0440\u0435\u0447\u0443",
  locationLabel: "\u041c\u0435\u0441\u0442\u043e",
  locationPlaceholder: "\u041d\u0435\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e",
  saveButton: "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",
  createButton: "\u0421\u043e\u0437\u0434\u0430\u0442\u044c",
  cancelButton: "\u041e\u0442\u043c\u0435\u043d\u0430",
  deleteButton: "\u0423\u0434\u0430\u043b\u0438\u0442\u044c"
};

export function EventEditorPage({ token, session }: { token: string; session: SessionPayload }) {
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
          setError(requestError instanceof Error ? requestError.message : EVENT_EDITOR_TEXT.loadError);
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

  function toggleParticipant(userId: number) {
    setSelectedIds((current) => {
      if (!current.includes(userId)) {
        setError(null);
        return [...current, userId];
      }
      if (current.length === 1) {
        setError(EVENT_EDITOR_TEXT.noParticipants);
        return current;
      }
      setError(null);
      return current.filter((id) => id !== userId);
    });
  }

  if (!workspace && eventId && loading) {
    return (
      <section className="editor-screen">
        <ScreenHeader title={EVENT_EDITOR_TEXT.loadTitle} eyebrow={EVENT_EDITOR_TEXT.formEyebrow} />
        <div className="empty-card">{EVENT_EDITOR_TEXT.loadMessage}</div>
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
          eyebrow={EVENT_EDITOR_TEXT.formEyebrow}
          title={eventId ? EVENT_EDITOR_TEXT.editTitle : EVENT_EDITOR_TEXT.createTitle}
          description={workspace.name}
        />
        <div className="notice">{EVENT_EDITOR_TEXT.adminOnly}</div>
      </section>
    );
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    if (!selectedIds.length) {
      setError(EVENT_EDITOR_TEXT.noParticipants);
      return;
    }

    if (endTime && endTime <= startTime) {
      setError(EVENT_EDITOR_TEXT.invalidEventTime);
      return;
    }

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
      setError(requestError instanceof Error ? requestError.message : EVENT_EDITOR_TEXT.saveError);
    }
  }

  async function handleDelete() {
    if (!eventId) {
      return;
    }
    if (!window.confirm("\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435?")) {
      return;
    }
    try {
      await deleteEvent(Number(eventId), token);
      navigate(`/workspaces/${workspace.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : EVENT_EDITOR_TEXT.deleteError);
    }
  }

  return (
    <section className="editor-screen">
      <ScreenHeader
        backTo={`/workspaces/${workspace.id}`}
        eyebrow={EVENT_EDITOR_TEXT.formEyebrow}
        title={eventId ? EVENT_EDITOR_TEXT.editTitle : EVENT_EDITOR_TEXT.createTitle}
        description={workspace.name}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {loading ? (
        <div className="empty-card">{EVENT_EDITOR_TEXT.loadMessage}</div>
      ) : (
        <form className="editor-form" onSubmit={handleSubmit}>
          <LineField label={EVENT_EDITOR_TEXT.titleLabel}>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </LineField>

          <LineField label={EVENT_EDITOR_TEXT.dateLabel}>
            <input type="date" value={eventDate} onChange={(event) => setEventDate(event.target.value)} required />
          </LineField>

          <LineField label={EVENT_EDITOR_TEXT.timeLabel}>
            <div className="time-fields">
              <input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
              <span>{EVENT_EDITOR_TEXT.untilLabel}</span>
              <input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
            </div>
          </LineField>

          <LineField label={EVENT_EDITOR_TEXT.descriptionLabel} multiline>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              placeholder={EVENT_EDITOR_TEXT.descriptionPlaceholder}
            />
          </LineField>

          <LineField label={EVENT_EDITOR_TEXT.locationLabel}>
            <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder={EVENT_EDITOR_TEXT.locationPlaceholder} />
          </LineField>

          <ParticipantSelector members={workspace.members} onToggle={toggleParticipant} selectedIds={selectedIds} />

          <div className="editor-actions">
            <button className="action-pill" type="submit">
              {eventId ? EVENT_EDITOR_TEXT.saveButton : EVENT_EDITOR_TEXT.createButton}
            </button>
            <button className="action-pill action-pill--ghost" type="button" onClick={() => navigate(`/workspaces/${workspace.id}`)}>
              {EVENT_EDITOR_TEXT.cancelButton}
            </button>
            {eventId ? (
              <button className="action-pill action-pill--danger" type="button" onClick={handleDelete}>
                {EVENT_EDITOR_TEXT.deleteButton}
              </button>
            ) : null}
          </div>
        </form>
      )}
    </section>
  );
}

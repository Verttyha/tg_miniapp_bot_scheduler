from __future__ import annotations

from datetime import datetime, timezone

from scheduler_app.domain.models import CalendarConnection, Event, Poll, User, Workspace
from scheduler_app.domain.schemas import (
    CalendarConnectionRead,
    CalendarOptionRead,
    EventRead,
    PollOptionRead,
    PollRead,
    StatsEntryRead,
    StatsSummaryRead,
    UserRead,
    WorkspaceRead,
)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def user_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


def workspace_read(workspace: Workspace) -> WorkspaceRead:
    return WorkspaceRead.model_validate(workspace)


def event_read(event: Event) -> EventRead:
    payload = EventRead.model_validate(event)
    payload.start_at = ensure_utc(payload.start_at)
    payload.end_at = ensure_utc(payload.end_at)
    payload.created_at = ensure_utc(payload.created_at)
    return payload


def connection_read(
    connection: CalendarConnection,
    *,
    calendars: list[dict[str, str]] | None = None,
) -> CalendarConnectionRead:
    base = CalendarConnectionRead.model_validate(connection)
    if base.token_expires_at:
        base.token_expires_at = ensure_utc(base.token_expires_at)
    if calendars:
        base.calendars = [CalendarOptionRead(**item) for item in calendars]
    return base


def poll_read(
    poll: Poll,
    *,
    user_vote_option_id: int | None = None,
) -> PollRead:
    vote_totals: dict[int, int] = {}
    for vote in poll.votes:
        vote_totals[vote.option_id] = vote_totals.get(vote.option_id, 0) + 1

    options = [
        PollOptionRead(
            id=option.id,
            label=option.label,
            start_at=ensure_utc(option.start_at),
            end_at=ensure_utc(option.end_at),
            vote_count=vote_totals.get(option.id, 0),
        )
        for option in poll.options
    ]
    return PollRead(
        id=poll.id,
        workspace_id=poll.workspace_id,
        title=poll.title,
        description=poll.description,
        timezone_name=poll.timezone_name,
        deadline_at=ensure_utc(poll.deadline_at),
        status=poll.status,
        selected_option_id=poll.selected_option_id,
        resulting_event_id=poll.resulting_event_id,
        participant_ids=poll.participant_ids,
        options=options,
        vote_totals=vote_totals,
        user_vote_option_id=user_vote_option_id,
        has_chat_poll=poll.telegram_chat_poll is not None,
    )


def stats_summary(workspace_id: int, entries: list[StatsEntryRead]) -> StatsSummaryRead:
    return StatsSummaryRead(
        workspace_id=workspace_id,
        generated_at=datetime.now(timezone.utc),
        entries=entries,
    )

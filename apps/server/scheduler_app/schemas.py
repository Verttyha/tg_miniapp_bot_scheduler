from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    joined_at: datetime
    user: UserRead


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    telegram_chat_id: int | None = None
    owner_user_id: int
    created_at: datetime
    members: list[WorkspaceMemberRead] = Field(default_factory=list)


class AuthInitDataRequest(BaseModel):
    init_data: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    user: UserRead
    workspaces: list[WorkspaceRead]


class CalendarOptionRead(BaseModel):
    id: str
    name: str


class CalendarConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    status: str
    account_email: str | None
    calendar_id: str | None
    calendar_name: str | None
    token_expires_at: datetime | None
    provider_metadata: dict[str, Any] | None
    calendars: list[CalendarOptionRead] = Field(default_factory=list)


class IntegrationLinkResponse(BaseModel):
    authorize_url: str
    provider: str


class IntegrationUpdateRequest(BaseModel):
    calendar_id: str | None = None
    calendar_name: str | None = None
    status: str | None = None


class EventParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendance_status: str
    user: UserRead


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    description: str | None
    location: str | None
    start_at: datetime
    end_at: datetime
    timezone_name: str
    status: str
    source: str
    created_at: datetime
    participants: list[EventParticipantRead] = Field(default_factory=list)


class EventCreateRequest(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    timezone_name: str = "Europe/Moscow"
    participant_ids: list[int]


class EventUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone_name: str | None = None
    participant_ids: list[int] | None = None


class AttendanceRecordInput(BaseModel):
    user_id: int
    status: str
    notes: str | None = None


class AttendanceUpdateRequest(BaseModel):
    records: list[AttendanceRecordInput]


class PollOptionInput(BaseModel):
    label: str | None = None
    start_at: datetime
    end_at: datetime


class PollCreateRequest(BaseModel):
    title: str
    description: str | None = None
    timezone_name: str = "Europe/Moscow"
    deadline_at: datetime
    participant_ids: list[int]
    options: list[PollOptionInput]


class PollOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str | None
    start_at: datetime
    end_at: datetime
    vote_count: int = 0


class VoteRequest(BaseModel):
    option_id: int


class PollResolveRequest(BaseModel):
    selected_option_id: int | None = None


class PollRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    description: str | None
    timezone_name: str
    deadline_at: datetime
    status: str
    selected_option_id: int | None
    resulting_event_id: int | None
    participant_ids: list[int]
    options: list[PollOptionRead] = Field(default_factory=list)
    vote_totals: dict[int, int] = Field(default_factory=dict)
    user_vote_option_id: int | None = None
    has_chat_poll: bool = False


class StatsEntryRead(BaseModel):
    user: UserRead
    attended: int
    missed: int
    invited: int
    attendance_rate: float


class StatsSummaryRead(BaseModel):
    workspace_id: int
    generated_at: datetime
    entries: list[StatsEntryRead]

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scheduler_app.domain.models import AttendanceStatus


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


class ExternalCalendarEventRead(BaseModel):
    id: str
    calendar_id: str
    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    html_link: str | None = None


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

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Нужно указать название")
        return value

    @field_validator("participant_ids")
    @classmethod
    def validate_participant_ids(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("Нужен хотя бы один участник")
        if len(set(value)) != len(value):
            raise ValueError("Участники не должны повторяться")
        return value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Время начала и окончания должно включать часовой пояс")
        if self.end_at <= self.start_at:
            raise ValueError("Время окончания должно быть позже времени начала")
        if not self.timezone_name.strip():
            raise ValueError("Нужно указать часовой пояс")
        return self


class EventUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone_name: str | None = None
    participant_ids: list[int] | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Нужно указать название")
        return value

    @field_validator("participant_ids")
    @classmethod
    def validate_optional_participant_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and not value:
            raise ValueError("Нужен хотя бы один участник")
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Участники не должны повторяться")
        return value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_at is not None and self.start_at.tzinfo is None:
            raise ValueError("Время начала должно включать часовой пояс")
        if self.end_at is not None and self.end_at.tzinfo is None:
            raise ValueError("Время окончания должно включать часовой пояс")
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("Время окончания должно быть позже времени начала")
        if self.timezone_name is not None and not self.timezone_name.strip():
            raise ValueError("Нужно указать часовой пояс")
        return self


class AttendanceRecordInput(BaseModel):
    user_id: int
    status: str
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed_statuses = {status.value for status in AttendanceStatus}
        if value not in allowed_statuses:
            raise ValueError("Неподдерживаемый статус посещаемости")
        return value


class AttendanceUpdateRequest(BaseModel):
    records: list[AttendanceRecordInput]


class PollOptionInput(BaseModel):
    label: str | None = None
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Время начала и окончания должно включать часовой пояс")
        if self.end_at <= self.start_at:
            raise ValueError("Вариант голосования должен заканчиваться позже начала")
        return self


class PollCreateRequest(BaseModel):
    title: str
    description: str | None = None
    timezone_name: str = "Europe/Moscow"
    deadline_at: datetime
    participant_ids: list[int]
    options: list[PollOptionInput]

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Нужно указать название")
        return value

    @field_validator("participant_ids")
    @classmethod
    def validate_poll_participants(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("Нужен хотя бы один участник")
        if len(set(value)) != len(value):
            raise ValueError("Участники не должны повторяться")
        return value

    @model_validator(mode="after")
    def validate_deadline(self):
        if self.deadline_at.tzinfo is None:
            raise ValueError("Дедлайн должен включать часовой пояс")
        if not self.timezone_name.strip():
            raise ValueError("Нужно указать часовой пояс")
        if len(self.options) < 2:
            raise ValueError("Нужно указать минимум два варианта")
        if len(self.options) > 10:
            raise ValueError("Нельзя указать больше десяти вариантов")
        return self


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

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.domain.models import AttendanceStatus, Event, EventParticipant, User, WorkspaceMember
from scheduler_app.domain.schemas import StatsEntryRead
from scheduler_app.services.common import NotFoundError, get_workspace_member
from scheduler_app.services.presenters import stats_summary, user_read


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_workspace_stats(self, user: User, workspace_id: int):
        membership = await get_workspace_member(self.session, workspace_id, user.id)
        if not membership:
            raise NotFoundError("Workspace not found")

        members = await self.session.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))
        )
        member_list = list(members)
        events = await self.session.scalars(
            select(Event)
            .where(Event.workspace_id == workspace_id)
            .options(selectinload(Event.participants).selectinload(EventParticipant.user))
        )

        counters: dict[int, dict[str, int]] = {
            member.user_id: {"invited": 0, "attended": 0, "missed": 0} for member in member_list
        }
        for event in events:
            for participant in event.participants:
                data = counters.setdefault(participant.user_id, {"invited": 0, "attended": 0, "missed": 0})
                data["invited"] += 1
                if participant.attendance_status == AttendanceStatus.PRESENT.value:
                    data["attended"] += 1
                if participant.attendance_status == AttendanceStatus.ABSENT.value:
                    data["missed"] += 1

        entries = []
        for member in member_list:
            data = counters[member.user_id]
            rate = 0.0
            if data["invited"]:
                rate = round((data["attended"] / data["invited"]) * 100, 2)
            entries.append(
                StatsEntryRead(
                    user=user_read(member.user),
                    attended=data["attended"],
                    missed=data["missed"],
                    invited=data["invited"],
                    attendance_rate=rate,
                )
            )
        return stats_summary(workspace_id, entries)

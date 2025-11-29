from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.lobby_member import LobbyMember


class LobbyMemberRepository:
    """Data access layer for lobby members."""

    def __init__(self, session: Session):
        self.session = session

    async def add_member(
        self, lobby_id: int, user_id: int, seat_no: Optional[int] = None
    ) -> LobbyMember:
        """Add a user to a lobby."""
        member = LobbyMember(lobby_id=lobby_id, user_id=user_id, seat_no=seat_no)
        self.session.add(member)
        self.session.commit()
        self.session.refresh(member)
        return member

    async def remove_member(self, lobby_id: int, user_id: int) -> bool:
        """Remove a user from a lobby. Returns True if member was removed."""
        stmt = delete(LobbyMember).where(
            LobbyMember.lobby_id == lobby_id,
            LobbyMember.user_id == user_id,
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0

    async def get_member(self, lobby_id: int, user_id: int) -> Optional[LobbyMember]:
        """Get a specific member from a lobby."""
        stmt = select(LobbyMember).where(
            LobbyMember.lobby_id == lobby_id,
            LobbyMember.user_id == user_id,
        )
        return self.session.scalar(stmt)

    async def list_members(self, lobby_id: int) -> list[LobbyMember]:
        """Get all members in a lobby, ordered by seat_no or joined_at."""
        stmt = (
            select(LobbyMember)
            .where(LobbyMember.lobby_id == lobby_id)
            .order_by(LobbyMember.seat_no, LobbyMember.joined_at)
        )
        return list(self.session.scalars(stmt).all())

    async def count_members(self, lobby_id: int) -> int:
        """Count the number of members in a lobby."""
        stmt = select(LobbyMember).where(LobbyMember.lobby_id == lobby_id)
        return len(list(self.session.scalars(stmt).all()))

    async def remove_all_members(self, lobby_id: int) -> None:
        """Remove all members from a lobby."""
        stmt = delete(LobbyMember).where(LobbyMember.lobby_id == lobby_id)
        self.session.execute(stmt)
        self.session.commit()


async def get_lobby_member_repository(
    db: Session = Depends(get_db),
) -> LobbyMemberRepository:
    return LobbyMemberRepository(db)

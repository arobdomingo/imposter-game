from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.lobby import Lobby


class LobbyRepository:
    """Data access layer for game lobbies."""

    def __init__(self, session: Session):
        self.session = session

    async def create(self, code: str, host_id: int) -> Lobby:
        lobby = Lobby(code=code, host_id=host_id)
        self.session.add(lobby)
        self.session.commit()
        self.session.refresh(lobby)
        return lobby

    async def get_by_code(self, code: str) -> Optional[Lobby]:
        stmt = select(Lobby).where(Lobby.code == code)
        return self.session.scalar(stmt)

    async def get_by_id(self, lobby_id: int) -> Optional[Lobby]:
        stmt = select(Lobby).where(Lobby.id == lobby_id)
        return self.session.scalar(stmt)

    async def update_status(self, lobby_id: int, status: str) -> None:
        stmt = update(Lobby).where(Lobby.id == lobby_id).values(status=status)
        self.session.execute(stmt)
        self.session.commit()


async def get_lobby_repository(db: Session = Depends(get_db)) -> LobbyRepository:
    return LobbyRepository(db)

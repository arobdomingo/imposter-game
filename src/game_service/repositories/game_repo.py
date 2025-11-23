from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.game import Game


class GameRepository:
    """Data access helper for games."""

    def __init__(self, session: Session):
        self.session = session

    async def create(self, lobby_id: int, mode: str = "aware") -> Game:
        game = Game(lobby_id=lobby_id, mode=mode)
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        return game

    async def get_by_id(self, game_id: int) -> Optional[Game]:
        stmt = select(Game).where(Game.id == game_id)
        return self.session.scalar(stmt)

    async def get_active_by_lobby(self, lobby_id: int) -> Optional[Game]:
        stmt = select(Game).where(Game.lobby_id == lobby_id, Game.status != "finished")
        return self.session.scalar(stmt)

    async def update_status(
        self, game_id: int, status: str, current_round: Optional[int] = None
    ) -> None:
        values: dict[str, object] = {"status": status}
        if current_round is not None:
            values["current_round"] = current_round
        stmt = update(Game).where(Game.id == game_id).values(**values)
        self.session.execute(stmt)
        self.session.commit()


async def get_game_repository(db: Session = Depends(get_db)) -> GameRepository:
    return GameRepository(db)

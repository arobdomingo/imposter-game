from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from shared.database import get_db
from game_service.models.player import Player


class PlayerRepository:
    """Data access helper for players within a game."""

    def __init__(self, session: Session):
        self.session = session

    async def add_player(
        self,
        game_id: int,
        user_id: int,
        seat_no: int,
        is_imposter: bool = False,
        word: Optional[str] = None,
    ) -> Player:
        player = Player(
            game_id=game_id,
            user_id=user_id,
            seat_no=seat_no,
            is_imposter=is_imposter,
            word=word,
        )
        self.session.add(player)
        self.session.commit()
        self.session.refresh(player)
        return player

    async def list_by_game(self, game_id: int) -> list[Player]:
        stmt = select(Player).where(Player.game_id == game_id).order_by(Player.seat_no)
        return list(self.session.scalars(stmt).all())

    async def list_players(self, game_id: int):
        return await self.list_by_game(game_id)

    async def get_by_user(self, game_id: int, user_id: int) -> Optional[Player]:
        stmt = select(Player).where(
            Player.game_id == game_id, Player.user_id == user_id
        )
        return self.session.scalar(stmt)

    async def get_by_id(self, player_id: int) -> Optional[Player]:
        stmt = select(Player).where(Player.id == player_id)
        return self.session.scalar(stmt)

    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        return await self.get_by_id(player_id)

    async def get_by_seat(self, game_id: int, seat_no: int) -> Optional[Player]:
        """Get a player by game_id and seat number."""
        stmt = select(Player).where(
            Player.game_id == game_id, Player.seat_no == seat_no
        )
        return self.session.scalar(stmt)

    async def update_score(self, player_id: int, score_delta: int) -> None:
        stmt = (
            update(Player)
            .where(Player.id == player_id)
            .values(score=Player.score + score_delta)
        )
        self.session.execute(stmt)
        self.session.commit()

    async def set_score(self, player_id: int, score: int) -> None:
        """Set the score for a player (not increment)."""
        stmt = update(Player).where(Player.id == player_id).values(score=score)
        self.session.execute(stmt)
        self.session.commit()

    async def update_word(self, player_id: int, word: str) -> None:
        stmt = update(Player).where(Player.id == player_id).values(word=word)
        self.session.execute(stmt)
        self.session.commit()

    async def remove_by_game(self, game_id: int) -> None:
        stmt = delete(Player).where(Player.game_id == game_id)
        self.session.execute(stmt)
        self.session.commit()


async def get_player_repository(db: Session = Depends(get_db)) -> PlayerRepository:
    return PlayerRepository(db)

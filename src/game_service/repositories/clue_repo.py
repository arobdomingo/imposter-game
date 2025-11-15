from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.clue import Clue


class ClueRepository:
    """Manage clue submissions for each round."""

    def __init__(self, session: Session):
        self.session = session

    async def create(
        self,
        game_id: int,
        player_id: int,
        round_number: int,
        clue_word: str,
        skipped: bool = False,
    ) -> Clue:
        clue = Clue(
            game_id=game_id,
            player_id=player_id,
            round_number=round_number,
            clue_word=clue_word,
            skipped=skipped,
        )
        self.session.add(clue)
        self.session.commit()
        self.session.refresh(clue)
        return clue

    async def get_by_player_round(
        self, game_id: int, player_id: int, round_number: int
    ) -> Optional[Clue]:
        stmt = select(Clue).where(
            Clue.game_id == game_id,
            Clue.player_id == player_id,
            Clue.round_number == round_number,
        )
        return self.session.scalar(stmt)

    async def list_by_game(self, game_id: int) -> list[Clue]:
        stmt = select(Clue).where(Clue.game_id == game_id).order_by(
            Clue.round_number, Clue.submitted_at
        )
        return list(self.session.scalars(stmt).all())

    async def list_by_round(self, game_id: int, round_number: int) -> list[Clue]:
        stmt = select(Clue).where(
            Clue.game_id == game_id,
            Clue.round_number == round_number,
        ).order_by(Clue.submitted_at)
        return list(self.session.scalars(stmt).all())


async def get_clue_repository(db: Session = Depends(get_db)) -> ClueRepository:
    return ClueRepository(db)




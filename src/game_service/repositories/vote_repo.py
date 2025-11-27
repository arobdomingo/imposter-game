from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.vote import Vote


class VoteRepository:
    """Data access helper for player votes."""

    def __init__(self, session: Session):
        self.session = session

    async def create(
        self, game_id: int, voter_id: int, target_id: Optional[int]
    ) -> Vote:
        vote = Vote(game_id=game_id, voter_id=voter_id, target_id=target_id)
        self.session.add(vote)
        self.session.commit()
        self.session.refresh(vote)
        return vote

    async def create_vote(self, game_id: int, voter_id: int, target_id: Optional[int]):
        # Alias required by test_vote_routes.py
        return await self.create(game_id, voter_id, target_id)

    async def get_by_voter(self, game_id: int, voter_id: int) -> Optional[Vote]:
        stmt = select(Vote).where(Vote.game_id == game_id, Vote.voter_id == voter_id)
        return self.session.scalar(stmt)

    async def list_by_game(self, game_id: int) -> list[Vote]:
        stmt = select(Vote).where(Vote.game_id == game_id).order_by(Vote.created_at)
        return list(self.session.scalars(stmt).all())

    async def clear_game_votes(self, game_id: int) -> None:
        stmt = delete(Vote).where(Vote.game_id == game_id)
        self.session.execute(stmt)
        self.session.commit()


async def get_vote_repository(db: Session = Depends(get_db)) -> VoteRepository:
    return VoteRepository(db)

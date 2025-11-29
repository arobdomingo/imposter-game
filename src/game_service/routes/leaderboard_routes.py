from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel

from shared.database import get_db
from game_service.repositories.game_repo import GameRepository, get_game_repository
from game_service.models.player import Player
from game_service.models.game import Game
from user_service.models.user import User

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    total_score: int
    games_played: int


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    scope: str  # "global" or "lobby"


@router.get("/global", response_model=LeaderboardResponse)
async def get_global_leaderboard(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get global leaderboard - top players across all games.
    """
    # Aggregate scores by user_id
    stmt = (
        select(
            Player.user_id,
            func.sum(Player.score).label("total_score"),
            func.count(func.distinct(Player.game_id)).label("games_played"),
        )
        .group_by(Player.user_id)
        .order_by(func.sum(Player.score).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()

    entries = []
    for rank, (user_id, total_score, games_played) in enumerate(results, start=1):
        # Get username
        user = db.query(User).filter(User.id == user_id).first()
        username = user.name if user else f"User {user_id}"

        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=user_id,
                username=username,
                total_score=int(total_score) if total_score else 0,
                games_played=int(games_played) if games_played else 0,
            )
        )

    return LeaderboardResponse(entries=entries, scope="global")


@router.get("/lobby/{lobby_id}", response_model=LeaderboardResponse)
async def get_lobby_leaderboard(
    lobby_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    game_repo: GameRepository = Depends(get_game_repository),
):
    """
    Get leaderboard for a specific lobby - scores from all games in this lobby.
    """
    # Get all games for this lobby (including finished ones)
    games = db.query(Game).filter(Game.lobby_id == lobby_id).all()
    game_ids = [g.id for g in games]

    if not game_ids:
        return LeaderboardResponse(entries=[], scope=f"lobby_{lobby_id}")

    # Aggregate scores by user_id for games in this lobby
    stmt = (
        select(
            Player.user_id,
            func.sum(Player.score).label("total_score"),
            func.count(func.distinct(Player.game_id)).label("games_played"),
        )
        .filter(Player.game_id.in_(game_ids))
        .group_by(Player.user_id)
        .order_by(func.sum(Player.score).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()

    entries = []
    for rank, (user_id, total_score, games_played) in enumerate(results, start=1):
        # Get username
        user = db.query(User).filter(User.id == user_id).first()
        username = user.name if user else f"User {user_id}"

        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=user_id,
                username=username,
                total_score=int(total_score) if total_score else 0,
                games_played=int(games_played) if games_played else 0,
            )
        )

    return LeaderboardResponse(entries=entries, scope=f"lobby_{lobby_id}")

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from pydantic import BaseModel

from game_service.repositories.game_repo import get_game_repository, GameRepository
from game_service.repositories.player_repo import (
    get_player_repository,
    PlayerRepository,
)

router = APIRouter(prefix="/games", tags=["chat"])


class ChatIn(BaseModel):
    player_id: int
    message: str


class ChatOut(BaseModel):
    player_id: int
    message: str
    sent_at: datetime


# simple in-memory per-game buffer for demo (persist to DB for production)
_IN_MEMORY_CHAT: dict[int, List[ChatOut]] = {}


@router.post("/{game_id}/chat", response_model=ChatOut)
async def post_chat(
    game_id: int,
    payload: ChatIn,
    game_repo: GameRepository = Depends(get_game_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
):
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status not in ("discussion", "voting"):
        raise HTTPException(status_code=403, detail="Chat closed in this phase")
    player = await player_repo.get_by_id(payload.player_id)
    if not player or player.game_id != game_id:
        raise HTTPException(status_code=403, detail="Player not in game")

    out = ChatOut(
        player_id=player.id, message=payload.message, sent_at=datetime.utcnow()
    )
    _IN_MEMORY_CHAT.setdefault(game_id, []).append(out)
    return out


@router.get("/{game_id}/chat", response_model=List[ChatOut])
async def get_chat(game_id: int):
    return _IN_MEMORY_CHAT.get(game_id, [])

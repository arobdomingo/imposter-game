from datetime import datetime

from pydantic import BaseModel

from .player import PlayerStateSchema
from .clue import ClueResponseSchema
from .vote import VoteResultSchema


class GameSummarySchema(BaseModel):
    id: int
    lobby_id: int
    status: str
    mode: str
    current_round: int
    created_at: datetime


class GameStateSchema(BaseModel):
    game: GameSummarySchema
    players: list[PlayerStateSchema]
    clues: list[ClueResponseSchema]
    votes: list[VoteResultSchema]

from datetime import datetime

from pydantic import BaseModel


class LobbyCreateSchema(BaseModel):
    host_id: int


class LobbyJoinSchema(BaseModel):
    user_id: int


class LobbyLeaveSchema(BaseModel):
    user_id: int


class LobbyResponseSchema(BaseModel):
    id: int
    code: str
    host_id: int
    status: str
    created_at: datetime


class LobbyPlayerSchema(BaseModel):
    user_id: int
    seat_no: int
    user_name: str | None = None  # Include user name to avoid extra API calls
    is_imposter: bool | None = None
    score: int | None = None


class LobbyStateSchema(BaseModel):
    lobby: LobbyResponseSchema
    players: list[LobbyPlayerSchema]
    active_game_id: int | None = None  # Include active game ID if lobby is playing

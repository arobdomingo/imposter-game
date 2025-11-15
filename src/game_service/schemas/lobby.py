from datetime import datetime

from pydantic import BaseModel


class LobbyCreateSchema(BaseModel):
    host_id: int


class LobbyJoinSchema(BaseModel):
    code: str
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
    is_imposter: bool | None = None
    score: int | None = None


class LobbyStateSchema(BaseModel):
    lobby: LobbyResponseSchema
    players: list[LobbyPlayerSchema]




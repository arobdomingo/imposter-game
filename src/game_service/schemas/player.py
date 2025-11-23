from pydantic import BaseModel


class PlayerStateSchema(BaseModel):
    id: int
    user_id: int
    seat_no: int
    is_imposter: bool
    word: str | None = None
    score: int

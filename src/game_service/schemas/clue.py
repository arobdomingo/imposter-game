from datetime import datetime

from pydantic import BaseModel, constr


class ClueSubmitSchema(BaseModel):
    player_id: int
    round_number: int
    clue_word: constr(min_length=1, max_length=64)  # type: ignore[valid-type]
    skipped: bool = False


class ClueResponseSchema(BaseModel):
    id: int
    player_id: int
    round_number: int
    clue_word: str
    skipped: bool
    submitted_at: datetime




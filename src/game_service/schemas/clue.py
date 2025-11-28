from datetime import datetime

from pydantic import BaseModel


class ClueSubmitSchema(BaseModel):
    player_id: int
    round_number: int
    clue_word: str = ""  # Allow empty string for skipped clues
    skipped: bool = False


class ClueResponseSchema(BaseModel):
    id: int
    player_id: int
    round_number: int
    clue_word: str
    skipped: bool
    submitted_at: datetime
    previous_clues: list[dict] = []  # Additional fields for response
    can_submit_next: bool = True
    move_to_voting: bool = False

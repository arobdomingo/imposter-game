'''from datetime import datetime

from pydantic import BaseModel
from typing import Dict


class VoteRequestSchema(BaseModel):
    voter_id: int
    target_id: int | None


class VoteResultSchema(BaseModel):
    id: int
    voter_id: int
    target_id: int | None
    created_at: datetime

class ScoreResultSchema(BaseModel):
    game_id: int
    impostor_id: int
    player_scores: Dict[int, int]'''

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class VoteRequestSchema(BaseModel):
    game_id: int
    voter_id: int
    target_id: Optional[int] = None  # None means abstain


class VoteResultSchema(BaseModel):
    id: int
    voter_id: int
    target_id: Optional[int] = None
    created_at: datetime


class ScoreResultSchema(BaseModel):
    game_id: int
    impostor_ids: List[int]  # align with scoring_service output
    player_scores: Dict[str, int]  # player_id -> score mapping

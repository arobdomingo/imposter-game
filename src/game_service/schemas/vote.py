

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class VoteRequestSchema(BaseModel):
    game_id: int
    voter_id: int
    target_id: Optional[int] = None  


class VoteResultSchema(BaseModel):
    id: int
    voter_id: int
    target_id: Optional[int] = None
    created_at: datetime


class ScoreResultSchema(BaseModel):
    game_id: int
    impostor_ids: List[int] 
    player_scores: Dict[str, int]  

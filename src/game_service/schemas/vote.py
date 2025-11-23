from datetime import datetime

from pydantic import BaseModel


class VoteRequestSchema(BaseModel):
    voter_id: int
    target_id: int | None


class VoteResultSchema(BaseModel):
    id: int
    voter_id: int
    target_id: int | None
    created_at: datetime

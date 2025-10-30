from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from user_service.models.friendship import (
    FriendshipRepository,
    get_friendship_repository,
    FriendshipSchema,
)

router = APIRouter(prefix="/friendships", tags=["Friendships"])

# Request body for creating a friendship
class FriendshipRequest(BaseModel):
    requester_id: int
    receiver_id: int

# Request body for creating a friendship
class FriendshipRequest(BaseModel):
    requester_id: int
    receiver_id: int


# -------- Create a friend request --------
@router.post("/request")
async def create_friend_request(
    body: FriendshipRequest,
    repo: FriendshipRepository = Depends(get_friendship_repository),
):
    try:
        await repo.send_request(body.requester_id, body.receiver_id)
        return {"status": "request sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------- Update a friend request --------
@router.put("/update")
async def update_friend_request(
    requester_id: int,
    receiver_id: int,
    accept: bool = True,
    repo: FriendshipRepository = Depends(get_friendship_repository),
):
    try:
        await repo.update_request(requester_id, receiver_id, accept)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------- Get incoming requests --------
@router.get("/incoming/{user_id}", response_model=list[FriendshipSchema])
async def get_incoming(
    user_id: int, repo: FriendshipRepository = Depends(get_friendship_repository)
):
    return [
        FriendshipSchema.from_db_model(f)
        for f in await repo.get_incoming_requests(user_id)
    ]


# -------- Get outgoing requests --------
@router.get("/outgoing/{user_id}", response_model=list[FriendshipSchema])
async def get_outgoing(
    user_id: int, repo: FriendshipRepository = Depends(get_friendship_repository)
):
    return [
        FriendshipSchema.from_db_model(f)
        for f in await repo.get_outgoing_requests(user_id)
    ]

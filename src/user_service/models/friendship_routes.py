from fastapi import APIRouter, Depends, HTTPException
from user_service.models.friendship import get_friendship_repository
import traceback

router = APIRouter(prefix="/friendships", tags=["Friendships"])

@router.post("/request")
async def send_friend_request(requester_id: int, receiver_id: int, repo=Depends(get_friendship_repository)):
    try:
        await repo.send_request(requester_id, receiver_id)
        return {"message": "Friend request sent"}
    except Exception:
        print("Error in send_request:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/accept")
async def accept_friend_request(requester_id: int, receiver_id: int, repo=Depends(get_friendship_repository)):
    try:
        await repo.accept_request(requester_id, receiver_id)
        return {"message": "Friend request accepted"}
    except Exception:
        print("Error in accept_request:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

from pydantic import BaseModel
from sqlalchemy import select, insert, update, delete, String, Integer, ForeignKey
from sqlalchemy.orm import Session, Mapped, mapped_column
from fastapi import Depends
from shared.database import get_db
from user_service.models.user import Base  # ✅ Use the shared declarative Base

# ------------------ DATABASE MODEL ------------------
class Friendship(Base):
    __tablename__ = "friendships"

    requester: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    receiver: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)  # "pending", "accepted"

# ------------------ REPOSITORY ------------------
class FriendshipRepository:
    def __init__(self, session: Session):
        self.session = session

    async def send_request(self, requester_id: int, receiver_id: int) -> None:
        existing = self.session.scalar(
            select(Friendship).where(
                ((Friendship.requester == requester_id) & (Friendship.receiver == receiver_id))
                | ((Friendship.requester == receiver_id) & (Friendship.receiver == requester_id))
            )
        )
        if existing:
            return
        self.session.execute(
            insert(Friendship),
            [{"requester": requester_id, "receiver": receiver_id, "status": "pending"}],
        )
        self.session.commit()

    async def update_request(self, requester_id: int, receiver_id: int, accept: bool) -> None:
        existing = self.session.scalar(
            select(Friendship).where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
        )
        if not existing:
            return
        new_status = "accepted" if accept else "rejected"
        stmt = (
            update(Friendship)
            .where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
            .values(status=new_status)
        )
        self.session.execute(stmt)
        self.session.commit()

    async def get_incoming_requests(self, user_id: int):
        results = self.session.execute(
            select(Friendship).where(Friendship.receiver == user_id, Friendship.status == "pending")
        )
        return [f for f, in results.all()]

    async def get_outgoing_requests(self, user_id: int):
        results = self.session.execute(
            select(Friendship).where(Friendship.requester == user_id, Friendship.status == "pending")
        )
        return [f for f, in results.all()]

    async def delete_request(self, requester_id: int, receiver_id: int):
        stmt = delete(Friendship).where(
            (Friendship.requester == requester_id) & (Friendship.receiver == receiver_id)
        )
        self.session.execute(stmt)
        self.session.commit()

# ------------------ DEPENDENCY ------------------
def get_friendship_repository(db: Session = Depends(get_db)) -> FriendshipRepository:
    return FriendshipRepository(db)

# ------------------ SCHEMA ------------------
class FriendshipSchema(BaseModel):
    requester: int
    receiver: int
    status: str

    @classmethod
    def from_db_model(cls, friendship: Friendship) -> "FriendshipSchema":
        return cls(
            requester=friendship.requester,
            receiver=friendship.receiver,
            status=friendship.status,
        )

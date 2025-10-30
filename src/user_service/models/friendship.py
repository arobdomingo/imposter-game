from pydantic import BaseModel
from sqlalchemy import select, insert, update, String, Integer
from sqlalchemy.orm import Session, mapped_column, Mapped
from fastapi import Depends
from shared.database import get_db

from user_service.models.user import Base  # Inherit from your SQLAlchemy Base

# ------------------ DATABASE MODEL ------------------


class Friendship(Base):
    """
    Friendship model used by SQLAlchemy to represent friendship relationships.
    """

    __tablename__ = "friendships"
    requester: Mapped[int] = mapped_column(Integer, primary_key=True)
    receiver: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "pending", "accepted"


# ------------------ REPOSITORY ------------------


class FriendshipRepository:
    """
    Controls manipulation of the friendships table.
    """

    def __init__(self, session: Session):
        self.session = session

    async def send_request(self, requester_id: int, receiver_id: int) -> None:
        existing = self.session.scalar(
            select(Friendship).where(
                (
                    (Friendship.requester == requester_id)
                    & (Friendship.receiver == receiver_id)
                )
                | (
                    (Friendship.requester == receiver_id)
                    & (Friendship.receiver == requester_id)
                )
            )
        )
        if existing:
            print(
                f"[DB] Friendship already exists or pending between {requester_id} and {receiver_id}"
            )
            return

        self.session.execute(
            insert(Friendship),
            [
                {
                    "requester": requester_id,
                    "receiver": receiver_id,
                    "status": "pending",
                }
            ],
        )
        self.session.commit()
        print(f"[DB] Friendship request sent from {requester_id} to {receiver_id}")

    async def accept_request(self, requester_id: int, receiver_id: int) -> None:
        existing = self.session.scalar(
            select(Friendship).where(
                (
                    (Friendship.requester == requester_id)
                    & (Friendship.receiver == receiver_id)
                )
                | (
                    (Friendship.requester == receiver_id)
                    & (Friendship.receiver == requester_id)
                )
            )
        )
        if not existing or existing.status != "pending":
            print(
                f"[DB] No pending request found to accept ({requester_id} -> {receiver_id})"
            )
            return

        stmt = (
            update(Friendship)
            .where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
            .values(status="accepted")
        )
        self.session.execute(stmt)
        self.session.commit()
        print(f"[DB] Friendship accepted between {requester_id} and {receiver_id}")


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

from pydantic import BaseModel
from sqlalchemy import (
    select,
    insert,
    update,
    delete as sa_delete,
    String,
    Integer,
    or_,
)
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

    async def reject_request(self, requester_id: int, receiver_id: int) -> None:
        existing = self.session.scalar(
            select(Friendship).where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
        )
        if not existing:
            return
        # Simple reject -> delete pending
        self.session.execute(
            sa_delete(Friendship).where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
        )
        self.session.commit()

    async def cancel_request(self, requester_id: int, receiver_id: int) -> None:
        # requester cancels their own pending request
        self.session.execute(
            sa_delete(Friendship).where(
                (Friendship.requester == requester_id)
                & (Friendship.receiver == receiver_id)
                & (Friendship.status == "pending")
            )
        )
        self.session.commit()

    async def get_incoming_requests(self, user_id: int) -> list[Friendship]:
        rows = self.session.scalars(
            select(Friendship).where(
                (Friendship.receiver == user_id) & (Friendship.status == "pending")
            )
        ).all()
        return list(rows)

    async def get_outgoing_requests(self, user_id: int) -> list[Friendship]:
        rows = self.session.scalars(
            select(Friendship).where(
                (Friendship.requester == user_id) & (Friendship.status == "pending")
            )
        ).all()
        return list(rows)

    async def list_friends(self, user_id: int) -> list[Friendship]:
        rows = self.session.scalars(
            select(Friendship).where(
                (Friendship.status == "accepted")
                & (or_(Friendship.requester == user_id, Friendship.receiver == user_id))
            )
        ).all()
        return list(rows)

    async def delete_friendship(self, user_id: int, friend_id: int) -> None:
        self.session.execute(
            sa_delete(Friendship).where(
                (Friendship.status == "accepted")
                & (
                    (Friendship.requester == user_id)
                    & (Friendship.receiver == friend_id)
                    | (Friendship.requester == friend_id)
                    & (Friendship.receiver == user_id)
                )
            )
        )
        self.session.commit()

    async def delete_all_for_user(self, user_id: int) -> None:
        # remove both pending and accepted involving the user
        self.session.execute(
            sa_delete(Friendship).where(
                or_(Friendship.requester == user_id, Friendship.receiver == user_id)
            )
        )
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

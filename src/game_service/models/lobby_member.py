from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models.user import Base


class LobbyMember(Base):
    """Tracks which users are currently in a lobby."""

    __tablename__ = "lobby_members"
    __table_args__ = (
        UniqueConstraint("lobby_id", "user_id", name="uq_lobby_members_lobby_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lobby_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lobbies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

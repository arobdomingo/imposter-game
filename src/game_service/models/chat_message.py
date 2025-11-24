from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models.user import Base


class ChatMessage(Base):
    """Stores chat messages during discussion/voting phases."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )  # "text" or "reaction"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

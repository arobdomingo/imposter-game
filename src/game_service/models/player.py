from datetime import datetime

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models.user import Base


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("game_id", "user_id", name="uq_players_game_user"),
        UniqueConstraint("game_id", "seat_no", name="uq_players_game_seat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seat_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_imposter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    word: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

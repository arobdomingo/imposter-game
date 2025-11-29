from datetime import datetime

from sqlalchemy import (
    Integer,
    DateTime,
    ForeignKey,
    String,
    Boolean,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models.user import Base


class Clue(Base):
    __tablename__ = "clues"
    __table_args__ = (
        UniqueConstraint(
            "game_id", "player_id", "round_number", name="uq_clues_per_round"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    clue_word: Mapped[str] = mapped_column(String(64), nullable=False)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

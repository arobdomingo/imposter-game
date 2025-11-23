from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models.user import Base


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("game_id", "voter_id", name="uq_votes_game_voter"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    voter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

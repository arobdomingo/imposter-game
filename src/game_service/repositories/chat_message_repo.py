from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.models.chat_message import ChatMessage


class ChatMessageRepository:
    """Data access layer for chat messages."""

    def __init__(self, session: Session):
        self.session = session

    async def create(
        self,
        game_id: int,
        user_id: int,
        message: str,
        message_type: str = "text",
    ) -> ChatMessage:
        """Create a new chat message."""
        chat_message = ChatMessage(
            game_id=game_id,
            user_id=user_id,
            message=message,
            message_type=message_type,
        )
        self.session.add(chat_message)
        self.session.commit()
        self.session.refresh(chat_message)
        return chat_message

    async def list_recent_by_game(
        self, game_id: int, limit: int = 50
    ) -> list[ChatMessage]:
        """Get recent chat messages for a game."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.game_id == game_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = list(self.session.scalars(stmt).all())
        # Return in chronological order (oldest first)
        return list(reversed(messages))

    async def list_by_game(self, game_id: int) -> list[ChatMessage]:
        """Get all chat messages for a game."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.game_id == game_id)
            .order_by(ChatMessage.created_at)
        )
        return list(self.session.scalars(stmt).all())


async def get_chat_message_repository(
    db: Session = Depends(get_db),
) -> ChatMessageRepository:
    return ChatMessageRepository(db)

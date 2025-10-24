from pydantic import BaseModel
from sqlalchemy import select, String, DateTime, Text, Integer, JSON, func
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy.exc import IntegrityError
from fastapi import Depends
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from shared.database import get_db
from user_service.models.user import Base  # Inherit from your SQLAlchemy Base


# ------------------ DATABASE MODEL ------------------

class Event(Base):
    """
    Event model used by SQLAlchemy to represent events in the database.
    Events are immutable once created.
    """

    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    when: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)


# ------------------ REPOSITORY ------------------

class EventRepository:
    """
    Controls manipulation of the events table.
    Events are immutable - no update or delete operations.
    """

    def __init__(self, session: Session):
        self.session = session

    async def create(
        self, 
        when: datetime, 
        source: str, 
        type: str, 
        payload: Dict[str, Any], 
        user: Optional[str] = None
    ) -> Event:
        """Create a new event. Events are immutable once created."""
        try:
            new_event = Event(
                when=when,
                source=source,
                type=type,
                payload=payload,
                user=user
            )
            self.session.add(new_event)
            self.session.commit()
            self.session.refresh(new_event)
            return new_event
        except IntegrityError:
            self.session.rollback()
            raise

    async def get_by_filters(
        self,
        type: Optional[str] = None,
        source: Optional[str] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        user: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Event], int]:
        """
        Get events filtered by various criteria with pagination.
        Returns (events, total_count).
        """
        # Build the query
        query = select(Event)
        
        # Apply filters
        if type is not None:
            query = query.where(Event.type == type)
        if source is not None:
            query = query.where(Event.source == source)
        if before is not None:
            query = query.where(Event.when < before)
        if after is not None:
            query = query.where(Event.when > after)
        if user is not None:
            query = query.where(Event.user == user)
        
        # Get total count for pagination
        count_query = select(func.count(Event.id))
        if query.whereclause is not None:
            count_query = count_query.where(query.whereclause)
        
        total_count = self.session.scalar(count_query)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Event.when.desc()).offset(offset).limit(page_size)
        
        events = self.session.scalars(query).all()
        return list(events), total_count

    async def get_all(self, page: int = 1, page_size: int = 50) -> Tuple[List[Event], int]:
        """Get all events with pagination."""
        return await self.get_by_filters(page=page, page_size=page_size)


# ------------------ DEPENDENCY ------------------

def get_event_repository(db: Session = Depends(get_db)) -> EventRepository:
    return EventRepository(db)


# ------------------ SCHEMAS ------------------

class EventCreateSchema(BaseModel):
    """Schema for creating an event"""
    when: datetime
    source: str
    type: str
    payload: Dict[str, Any]
    user: Optional[str] = None


class EventResponseSchema(BaseModel):
    """Schema for event responses"""
    id: int
    when: datetime
    source: str
    type: str
    payload: Dict[str, Any]
    user: Optional[str] = None

    @classmethod
    def from_db_model(cls, event: Event) -> "EventResponseSchema":
        """Create an EventResponseSchema from an Event"""
        return cls(
            id=event.id,
            when=event.when,
            source=event.source,
            type=event.type,
            payload=event.payload,
            user=event.user
        )


class EventQuerySchema(BaseModel):
    """Schema for event query parameters"""
    type: Optional[str] = None
    source: Optional[str] = None
    before: Optional[datetime] = None
    after: Optional[datetime] = None
    user: Optional[str] = None
    page: int = 1
    page_size: int = 50


class PaginatedEventsResponse(BaseModel):
    """Response model for paginated events"""
    events: List[EventResponseSchema]
    total: int
    page: int
    page_size: int
    total_pages: int

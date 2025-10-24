from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import datetime
import math

from .event import (
    EventRepository,
    EventCreateSchema,
    EventResponseSchema,
    PaginatedEventsResponse,
    get_event_repository
)

router = APIRouter(prefix="/v2/events", tags=["Events"])


@router.post("/", status_code=201)
async def create_event(
    event: EventCreateSchema,
    repo: EventRepository = Depends(get_event_repository)
):
    """Create a new event. Events are immutable once created."""
    try:
        new_event = await repo.create(
            when=event.when,
            source=event.source,
            type=event.type,
            payload=event.payload,
            user=event.user
        )
        return {"event": EventResponseSchema.from_db_model(new_event)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


@router.get("/", response_model=PaginatedEventsResponse)
async def get_events(
    type: Optional[str] = Query(None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by source URL"),
    before: Optional[datetime] = Query(None, description="Filter events before this datetime"),
    after: Optional[datetime] = Query(None, description="Filter events after this datetime"),
    user: Optional[str] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of events per page"),
    repo: EventRepository = Depends(get_event_repository)
):
    """
    Get events with optional filtering by type, source, time range, and user.
    Events are returned in reverse chronological order (newest first).
    """
    try:
        events, total_count = await repo.get_by_filters(
            type=type,
            source=source,
            before=before,
            after=after,
            user=user,
            page=page,
            page_size=page_size
        )
        
        event_responses = [EventResponseSchema.from_db_model(event) for event in events]
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
        
        return PaginatedEventsResponse(
            events=event_responses,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")



import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .crud import create_event_crud, get_all_events_crud, update_event_crud
from .database import get_async_session
from .schemas import EventCreate, EventResponse, EventUpdate

events_router = APIRouter()

logger = logging.getLogger(__name__)


@events_router.post(
    "/", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    event: EventCreate, session: AsyncSession = Depends(get_async_session)
):
    try:
        return await create_event_crud(session, event)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"Unexpected error occurred while creating event: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@events_router.get("/", response_model=list[EventResponse])
async def get_all_events(
    offset: int = 0, limit: int = 10, session: AsyncSession = Depends(get_async_session)
):
    try:
        return await get_all_events_crud(session, offset, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"Unexpected error occurred while getting all events: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@events_router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_update: EventUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await update_event_crud(session, event_id, event_update)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"Unexpected error while updating event {event_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )

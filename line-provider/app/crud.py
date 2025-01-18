import json
import logging
from datetime import datetime

from fastapi import status, HTTPException
from sqlalchemy import and_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .models import events
from .rabbitmq import send_message
from .schemas import EventCreate, EventResponse, EventStatus, EventUpdate

logger = logging.getLogger(__name__)


async def create_event_crud(session: AsyncSession, event: EventCreate) -> EventResponse:
    query = (
        events.insert()
        .values(
            name=event.name,
            description=event.description,
            coef_1st_team_win=event.coef_1st_team_win,
            coef_2nd_team_win=event.coef_2nd_team_win,
            deadline=event.deadline,
            status=event.status,
        )
        .returning(events)
    )

    try:
        result = await session.execute(query)
        await session.commit()
        created_event = result.mappings().fetchone()

        if created_event is None:
            logger.error("Event not found after creation.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )

        return EventResponse(**created_event)

    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Failed to create event. Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def get_all_events_crud(
    session: AsyncSession, offset: int = 0, limit: int = 10
) -> list[EventResponse]:
    query = select(events).offset(offset).limit(limit).order_by(events.c.id)

    try:
        result = await session.execute(query)
        events_list = result.mappings().fetchall()
        return [EventResponse(**event) for event in events_list]

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching all events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def get_available_events(session: AsyncSession) -> list[EventResponse] | None:
    current_time = datetime.now()

    query = select(events).where(events.c.deadline > current_time).order_by(events.c.id)

    try:
        result = await session.execute(query)
        events_list = result.mappings().fetchall()
        return [EventResponse(**event) for event in events_list]

    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching available events: {e}", exc_info=True
        )
        return None


async def get_available_event_detail(
    session: AsyncSession, event_id: int
) -> EventResponse | None:
    current_time = datetime.now()

    query = select(events).where(
        and_(events.c.id == event_id, events.c.deadline > current_time)
    )

    try:
        result = await session.execute(query)
        event = result.mappings().fetchone()

        if event is None:
            logger.warning(
                f"Event with ID {event_id} not found or deadline has passed."
            )
            return None

        return EventResponse(**event)

    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching available event detail: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def update_event_crud(
    session: AsyncSession, event_id: int, event_update: EventUpdate
) -> EventResponse:
    query = select(events).where(events.c.id == event_id)
    result = await session.execute(query)
    updating_event = result.mappings().fetchone()

    if updating_event is None:
        logger.error(f"Event with id {event_id} not found", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    old_status = updating_event["status"]
    update_data = event_update.dict(exclude_unset=True)

    if "status" in update_data and update_data["status"] in (
        EventStatus.FIRST_TEAM_WON,
        EventStatus.SECOND_TEAM_WON,
    ):
        update_data["deadline"] = datetime.now()

    try:
        update_query = (
            update(events)
            .where(events.c.id == event_id)
            .values(**update_data)
            .execution_options(synchronize_session="fetch")
            .returning(events)
        )

        result = await session.execute(update_query)
        await session.commit()
        updated_event = result.mappings().fetchone()

        if updated_event is None:
            logger.error(
                f"Event with id {event_id} not found after update", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )

        if "status" in update_data:
            new_status = updated_event["status"]

            if old_status != new_status:
                event_data = {"event_id": event_id, "new_status": new_status}
                logger.info("Sending status update message in broker")

                try:
                    await send_message(
                        "bet-status-update",
                        json.dumps(event_data),
                        "event_updates_queue",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send status update message: {e}", exc_info=True
                    )

        return EventResponse(**updated_event)

    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error while updating event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )

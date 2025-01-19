import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi_cache.decorator import cache

from app.config import REQUEST_QUEUE_NAME
from app.rabbitmq import consume_response_from_queue, send_message
from app.schemas import EventResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/")
@cache(expire=30)
async def request_available_events() -> list[EventResponse]:
    try:
        correlation_id = str(uuid.uuid4())

        await send_message(
            routing_key="bet-request",
            message=json.dumps({"request": "get_available_events"}),
            queue_name=REQUEST_QUEUE_NAME,
            correlation_id=correlation_id,
        )
        logger.info(
            f"Sent request for available events with correlation_id: {correlation_id}",
        )

        response_data = await consume_response_from_queue(correlation_id)

        if response_data and "error" in response_data:
            logger.error(f"No response received for correlation_id: {correlation_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while getting available events has occured.",
            )

    except json.JSONDecodeError:
        logger.exception(
            f"Error decoding JSON response for correlation_id: {correlation_id}",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error decoding response data.",
        )
    except Exception:
        logger.exception("Error during request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error has occured.",
        )
    else:
        if response_data is None:
            logger.info(
                f"Received response for correlation_id: {correlation_id} with no events.",
            )
            return []
        logger.info(
            f"Received response for correlation_id: {correlation_id} with {len(response_data)} events.",
        )
        return [EventResponse(**event) for event in response_data]

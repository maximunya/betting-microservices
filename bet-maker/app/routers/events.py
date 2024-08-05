import json
import logging
import time
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi_cache.decorator import cache

from ..config import REQUEST_QUEUE_NAME
from ..rabbitmq import consume_response_from_queue, send_message
from ..schemas import EventResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/", response_model=List[EventResponse])
@cache(expire=30)
async def request_available_events():
    try:
        correlation_id = str(uuid.uuid4())

        await send_message(
            routing_key="bet-request",
            message=json.dumps({"request": "get_available_events"}),
            queue_name=REQUEST_QUEUE_NAME,
            correlation_id=correlation_id,
        )
        logger.info(
            f"Sent request for available events with correlation_id: {correlation_id}"
        )

        response_data = await consume_response_from_queue(correlation_id)

        if "error" in response_data:
            logger.error(f"No response received for correlation_id: {correlation_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error while getting available events has occured.",
            )

        logger.info(
            f"Received response for correlation_id: {correlation_id} with {len(response_data)} events."
        )
        return response_data

    except Exception as e:
        logger.error(f"Error during request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error has occured.",
        )

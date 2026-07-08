import logging

from fastapi import APIRouter, HTTPException, status
from fastapi_cache.decorator import cache

from ..config import REQUEST_QUEUE_NAME
from ..rabbitmq import rpc_call
from ..schemas import EventResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/", response_model=list[EventResponse])
@cache(expire=30)
async def request_available_events():
    try:
        response_data = await rpc_call(
            routing_key="bet-request",
            queue_name=REQUEST_QUEUE_NAME,
            payload={"request": "get_available_events"},
        )
    except TimeoutError as e:
        logger.error(f"Timed out waiting for available events: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Line provider service did not respond in time.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error has occurred.",
        )

    if "error" in response_data:
        logger.error(
            f"Error response while getting available events: {response_data['error']}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while getting available events has occurred.",
        )

    logger.info(f"Received {len(response_data)} available events")
    return response_data

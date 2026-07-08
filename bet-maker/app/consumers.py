import asyncio
import json
import logging

from aio_pika import IncomingMessage

from .config import EVENT_UPDATE_QUEUE_NAME
from .crud import update_bets_status
from .database import get_async_session
from .rabbitmq import get_rabbit_connection

logger = logging.getLogger(__name__)


async def process_event_update_message(message: IncomingMessage) -> None:
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            event_id = event_data["event_id"]
            new_status = event_data["new_status"]

            logger.info(
                f"Received event update: ID={event_id}, New Status={new_status}"
            )

            async for session in get_async_session():
                await update_bets_status(session, event_id, new_status)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)


async def consume() -> None:
    connection = await get_rabbit_connection()
    async with connection:
        channel = await connection.channel()

        event_updates_queue = await channel.declare_queue(
            EVENT_UPDATE_QUEUE_NAME, durable=True
        )
        await event_updates_queue.consume(process_event_update_message)
        logger.info("Consuming messages from event updates queue...")

        await asyncio.Future()

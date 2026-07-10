import asyncio
import json
import logging

from aio_pika import IncomingMessage, Message
from aio_pika.abc import AbstractChannel

from .config import REQUEST_QUEUE_NAME
from .crud import get_available_event_detail, get_available_events
from .database import get_async_session
from .rabbitmq import connect_with_retry, custom_json_serializer

logger = logging.getLogger(__name__)


async def process_request_message(
    message: IncomingMessage, channel: AbstractChannel
) -> None:
    async with message.process():
        try:
            request_data = json.loads(message.body.decode())
            request_type = request_data.get("request")

            async for session in get_async_session():
                if request_type == "get_available_events":
                    events = await get_available_events(session)
                    if events is None:
                        response_data = {
                            "error": "Error during getting available events occurred."
                        }
                    else:
                        response_data = [event.model_dump() for event in events]

                elif request_type == "get_available_event_detail":
                    event_id = request_data.get("event_id")
                    event = await get_available_event_detail(session, event_id)
                    if event is None:
                        response_data = {
                            "error": "Event not found or deadline has passed"
                        }
                    else:
                        response_data = event.model_dump()

                else:
                    logger.error(f"Unsupported request type: {request_type}")
                    return

                if message.reply_to is None:
                    logger.error(
                        "Request message has no reply_to, cannot send response"
                    )
                    return

                response_body = json.dumps(
                    response_data, default=custom_json_serializer
                )

                await channel.default_exchange.publish(
                    Message(
                        body=response_body.encode(),
                        correlation_id=message.correlation_id,
                    ),
                    routing_key=message.reply_to,
                )

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)


async def consume() -> None:
    connection = await connect_with_retry()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(REQUEST_QUEUE_NAME, durable=True)

        async def handler(message: IncomingMessage) -> None:
            await process_request_message(message, channel)

        await queue.consume(handler)
        logger.info("Consuming messages from queue...")

        await asyncio.Future()

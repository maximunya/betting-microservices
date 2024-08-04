import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Union

from aio_pika import (Connection, ExchangeType, IncomingMessage, Message,
                      connect_robust)

from .config import (EXCHANGE_NAME, RABBITMQ_HOST, RABBITMQ_PASS,
                     RABBITMQ_USER, REQUEST_QUEUE_NAME, RESPONSE_QUEUE_NAME)
from .database import get_async_session

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"

logger = logging.getLogger(__name__)


async def get_rabbit_connection() -> Connection:
    return await connect_robust(RABBITMQ_URL)


def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    logger.error(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


async def send_message(
    routing_key: str,
    message: Union[str, bytes],
    queue_name: str,
    correlation_id: str = None,
):
    connection = await get_rabbit_connection()
    async with connection:
        async with connection.channel() as channel:
            exchange = await channel.declare_exchange(
                EXCHANGE_NAME, ExchangeType.DIRECT, durable=True
            )

            queue = await channel.declare_queue(queue_name, durable=True)
            await queue.bind(exchange, routing_key=routing_key)

            await exchange.publish(
                Message(
                    body=message.encode() if isinstance(message, str) else message,
                    correlation_id=correlation_id,
                ),
                routing_key=routing_key,
            )


async def process_request_message(message: IncomingMessage):
    async with message.process():
        try:
            request_data = json.loads(message.body.decode())
            request_type = request_data.get("request")

            async for session in get_async_session():
                if request_type == "get_available_events":
                    from .crud import get_available_events

                    events = await get_available_events(session)

                    if events is None:
                        response_data = {"error": "Error during getting available events occurred."}
                    else:
                        response_data = [event.dict() for event in events]

                elif request_type == "get_available_event_detail":
                    from .crud import get_available_event_detail

                    event_id = request_data.get("event_id")
                    event = await get_available_event_detail(session, event_id)

                    if event is None:
                        response_data = {"error": "Event not found or deadline has passed"}
                    else:
                        response_data = event.dict()

                else:
                    logger.error(f"Unsupported request type: {request_type}")
                    raise ValueError(f"Unsupported request type: {request_type}")

                response_message = json.dumps(
                    response_data, default=custom_json_serializer
                )

                await send_message(
                    routing_key="event-response",
                    message=response_message,
                    queue_name=RESPONSE_QUEUE_NAME,
                    correlation_id=message.correlation_id,
                )

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)


async def consume():
    connection = await get_rabbit_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(REQUEST_QUEUE_NAME, durable=True)

        await queue.consume(process_request_message)
        logger.info("Consuming messages from queue...")

        await asyncio.Future()

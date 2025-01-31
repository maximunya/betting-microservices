import asyncio
import json
import logging
from typing import Optional, Union

from aio_pika import (Connection, ExchangeType, IncomingMessage, Message,
                      connect_robust)

from .config import (EVENT_UPDATE_QUEUE_NAME, EXCHANGE_NAME, RABBITMQ_HOST,
                     RABBITMQ_PASS, RABBITMQ_USER, RESPONSE_QUEUE_NAME)
from .crud import update_bets_status
from .database import get_async_session

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"

logger = logging.getLogger(__name__)


async def get_rabbit_connection() -> Connection:
    return await connect_robust(RABBITMQ_URL)


async def send_message(
    routing_key: str, message: Union[str, bytes], queue_name: str, correlation_id: str
) -> None:
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
            logger.error(f"Error processing message: {e}")


async def consume_response_from_queue(correlation_id: str) -> Optional[dict]:
    connection = await get_rabbit_connection()
    async with connection:
        async with connection.channel() as channel:
            event_response_queue = await channel.declare_queue(
                RESPONSE_QUEUE_NAME, durable=True
            )
            async for message in event_response_queue.iterator():
                async with message.process():
                    if message.correlation_id == correlation_id:
                        try:
                            response_data = json.loads(message.body.decode())
                            logger.info(f"Received available events: {response_data}")
                            return response_data
                        except Exception as e:
                            logger.error(f"Error processing response: {e}")


async def consume() -> None:
    connection = await connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        event_updates_queue = await channel.declare_queue(
            EVENT_UPDATE_QUEUE_NAME, durable=True
        )
        await event_updates_queue.consume(process_event_update_message)
        logger.info("Consuming messages from event updates queue...")

        await asyncio.Future()

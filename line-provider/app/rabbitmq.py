import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Union

from aio_pika import Connection, ExchangeType, Message, connect_robust

from .config import EXCHANGE_NAME, RABBITMQ_HOST, RABBITMQ_PASS, RABBITMQ_USER

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"

logger = logging.getLogger(__name__)


async def get_rabbit_connection() -> Connection:
    return await connect_robust(RABBITMQ_URL)


async def connect_with_retry(max_attempts: int = 10, delay: float = 3.0) -> Connection:
    """
    aio_pika.connect_robust only reconnects after the first connection succeeds,
    so we need to retry that first attempt by ourselves.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await get_rabbit_connection()
        except Exception as e:
            if attempt == max_attempts:
                raise
            logger.warning(
                f"RabbitMQ not reachable yet (attempt {attempt}/{max_attempts}): {e}"
            )
            await asyncio.sleep(delay)


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

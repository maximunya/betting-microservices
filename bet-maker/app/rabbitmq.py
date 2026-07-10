import asyncio
import json
import logging
import uuid

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


async def rpc_call(
    routing_key: str, queue_name: str, payload: dict, timeout: float = 10.0
) -> dict:
    """
    Request/response over RabbitMQ using a private, auto-deleted reply queue
    per call, so concurrent callers can never consume each other's responses
    (unlike scanning one shared response queue), and a timeout so a caller
    can't hang forever if nothing ever replies.
    """
    connection = await get_rabbit_connection()
    async with connection:
        channel = await connection.channel()
        callback_queue = await channel.declare_queue(exclusive=True, auto_delete=True)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.DIRECT, durable=True
        )
        request_queue = await channel.declare_queue(queue_name, durable=True)
        await request_queue.bind(exchange, routing_key=routing_key)

        correlation_id = str(uuid.uuid4())
        await exchange.publish(
            Message(
                body=json.dumps(payload).encode(),
                correlation_id=correlation_id,
                reply_to=callback_queue.name,
            ),
            routing_key=routing_key,
        )
        logger.info(
            f"Sent RPC request '{routing_key}' (correlation_id={correlation_id})"
        )

        try:
            async with callback_queue.iterator() as queue_iter:
                async with asyncio.timeout(timeout):
                    async for message in queue_iter:
                        async with message.process():
                            if message.correlation_id == correlation_id:
                                logger.info(
                                    f"Received RPC response (correlation_id={correlation_id})"
                                )
                                return json.loads(message.body.decode())
        except TimeoutError:
            logger.error(
                f"RPC call '{routing_key}' timed out after {timeout}s "
                f"(correlation_id={correlation_id})"
            )
            raise TimeoutError(
                f"No response received for '{routing_key}' within {timeout}s"
            )

import os

from dotenv import load_dotenv

load_dotenv()


DB_HOST: str = os.environ.get("DB_HOST", "postgres")
DB_PORT: int = int(os.environ.get("DB_PORT", 5432))
DB_NAME: str = os.environ.get("DB_NAME", "postgres")
DB_USER: str = os.environ.get("DB_USER", "postgres")
DB_PASS: str = os.environ.get("DB_PASS", "postgres")

RABBITMQ_USER: str = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASS: str = os.environ.get("RABBITMQ_PASS", "guest")
RABBITMQ_HOST: str = os.environ.get("RABBITMQ_HOST", "rabbitmq")

EXCHANGE_NAME: str = os.environ.get("EXCHANGE_NAME", "default_exchange")
EVENT_UPDATE_QUEUE_NAME: str = os.environ.get(
    "EVENT_UPDATE_QUEUE_NAME", "event_updates_queue",
)
REQUEST_QUEUE_NAME: str = os.environ.get("REQUEST_QUEUE_NAME", "bet_request_queue")
RESPONSE_QUEUE_NAME: str = os.environ.get("RESPONSE_QUEUE_NAME", "event_response_queue")

REDIS_HOST: str = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT: int = int(os.environ.get("REDIS_PORT", 6379))

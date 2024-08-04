import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

RABBITMQ_USER = os.environ.get("RABBITMQ_USER")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")

EXCHANGE_NAME = os.environ.get("EXCHANGE_NAME")
EVENT_UPDATE_QUEUE_NAME = os.environ.get("EVENT_UPDATE_QUEUE_NAME")
REQUEST_QUEUE_NAME = os.environ.get("REQUEST_QUEUE_NAME")
RESPONSE_QUEUE_NAME = os.environ.get("RESPONSE_QUEUE_NAME")

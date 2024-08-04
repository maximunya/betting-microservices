import asyncio
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from .rabbitmq import consume
from .router import events_router

app = FastAPI(title="Line Provider")

app.include_router(events_router, prefix="/events", tags=["events"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("logs/app.log", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    try:
        asyncio.create_task(consume())
        logger.info("RabbitMQ consumer started successfully.")
    except Exception as e:
        logger.error(f"Failed to start RabbitMQ consumer: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down.")

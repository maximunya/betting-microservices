import asyncio
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from .config import REDIS_HOST, REDIS_PORT
from .rabbitmq import consume
from .routers import bets, events

app = FastAPI(title="Bet Maker", root_path="/bet-maker")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bets.router, prefix="/bets", tags=["bets"])
app.include_router(events.router, prefix="/events", tags=["events"])


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
    redis = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

    try:
        await asyncio.sleep(5)
        asyncio.create_task(consume())
        logger.info("RabbitMQ consumer started successfully.")
    except Exception as e:
        logger.error(f"Failed to start RabbitMQ consumer: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down.")

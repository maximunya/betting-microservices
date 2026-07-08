import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .consumers import consume
from .router import events_router

app = FastAPI(title="Line Provider", root_path="/line-provider")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router, prefix="/events", tags=["events"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume())
    logger.info("RabbitMQ consumer started.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down.")

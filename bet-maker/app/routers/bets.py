import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_async_session
from app.schemas import BetCreate, BetResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/", response_model=BetResponse, status_code=status.HTTP_201_CREATED)
async def place_bet(
    bet: BetCreate, session: Annotated[AsyncSession, Depends(get_async_session)],
):
    try:
        return await crud.create_bet(bet, session)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while placing bet")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@router.get("/", response_model=list[BetResponse])
async def list_bets(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    offset: int = 0,
    limit: int = 10,
):
    try:
        return await crud.get_all_bets(session, offset, limit)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while getting all bets")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )

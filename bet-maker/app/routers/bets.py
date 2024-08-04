import logging

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..database import get_async_session
from ..schemas import BetCreate, BetResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/", response_model=BetResponse, status_code=status.HTTP_201_CREATED)
async def place_bet(bet: BetCreate, session: AsyncSession = Depends(get_async_session)):
    try:
        return await crud.create_bet(bet, session)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error while placing bet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@router.get("/", response_model=list[BetResponse])
async def list_bets(
    offset: int = 0, limit: int = 10, session: AsyncSession = Depends(get_async_session)
):
    try:
        return await crud.get_all_bets(session, offset, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error while getting all bets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )

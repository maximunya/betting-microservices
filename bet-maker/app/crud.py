import json
import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import REQUEST_QUEUE_NAME
from app.models import bets
from app.schemas import BetCreate, BetPrediction, BetResponse, BetStatus, EventStatus

logger = logging.getLogger(__name__)


async def create_bet(bet: BetCreate, session: AsyncSession) -> BetResponse:
    from .rabbitmq import consume_response_from_queue, send_message

    correlation_id = str(uuid.uuid4())

    try:
        await send_message(
            routing_key="bet-request",
            message=json.dumps(
                {"request": "get_available_event_detail", "event_id": bet.event_id},
            ),
            queue_name=REQUEST_QUEUE_NAME,
            correlation_id=correlation_id,
        )
        logger.info(
            f"Sent request for available event detail with correlation_id: {correlation_id}",
        )

        response_data = await consume_response_from_queue(correlation_id)

        if "error" in response_data:
            logger.error(f"{response_data['error']}. event_id: {bet.event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Available event not found.",
            )

        coef_1st_team_win = Decimal(response_data.get("coef_1st_team_win"))
        coef_2nd_team_win = Decimal(response_data.get("coef_2nd_team_win"))

        coefficient = (
            coef_1st_team_win
            if bet.bet_prediction == "FIRST_TEAM_WIN"
            else coef_2nd_team_win
        )
        possible_winning = Decimal(bet.amount) * coefficient

        query = (
            bets.insert()
            .values(
                event_id=bet.event_id,
                bet_prediction=bet.bet_prediction,
                coefficient=coefficient,
                amount=bet.amount,
                possible_winning=possible_winning,
                status=BetStatus.NOT_PLAYED,
            )
            .returning(bets)
        )

        result = await session.execute(query)
        await session.commit()
        created_bet = result.mappings().fetchone()

        return BetResponse(**created_bet)

    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Database error occurred while creating bet")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def get_all_bets(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
) -> list[BetResponse]:
    query = select(bets).offset(offset).limit(limit).order_by(bets.c.id)

    try:
        result = await session.execute(query)
        bets_list = result.mappings().fetchall()
        return [BetResponse(**bet) for bet in bets_list]

    except SQLAlchemyError:
        logger.exception("Database error while retrieving bets")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def update_bets_status(
    session: AsyncSession,
    event_id: int,
    new_event_status: EventStatus,
) -> None:
    winning_prediction = (
        BetPrediction.FIRST_TEAM_WIN
        if new_event_status == EventStatus.FIRST_TEAM_WON
        else BetPrediction.SECOND_TEAM_WIN
    )
    try:
        update_won_query = (
            update(bets)
            .where(
                and_(
                    bets.c.event_id == event_id,
                    bets.c.bet_prediction == winning_prediction,
                ),
            )
            .values(status=BetStatus.WON)
        )

        await session.execute(update_won_query)

        update_lost_query = (
            update(bets)
            .where(
                and_(
                    bets.c.event_id == event_id,
                    bets.c.bet_prediction != winning_prediction,
                ),
            )
            .values(status=BetStatus.LOST)
        )

        await session.execute(update_lost_query)
        await session.commit()
        logger.info(f"Bet statuses successfully updated for event_id: {event_id}")

    except SQLAlchemyError:
        await session.rollback()
        logger.exception(
            f"Error occurred while updating bet statuses for event_id: {event_id}",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )

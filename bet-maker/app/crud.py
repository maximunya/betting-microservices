import json
import logging
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import and_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import REQUEST_QUEUE_NAME
from app.models import bets
from app.schemas import BetCreate, BetPrediction, BetResponse, BetStatus, EventStatus

logger = logging.getLogger(__name__)


async def send_bet_request(bet_event_id: int, correlation_id: str) -> None:
    """Отправка запроса на получение данных события."""
    from app.rabbitmq import send_message

    await send_message(
        routing_key="bet-request",
        message=json.dumps(
            {"request": "get_available_event_detail", "event_id": bet_event_id},
        ),
        queue_name=REQUEST_QUEUE_NAME,
        correlation_id=correlation_id,
    )
    logger.info(
        f"Sent request for available event detail with correlation_id: {correlation_id}",
    )


async def get_event_details(correlation_id: str) -> dict[str, str] | None:
    """Получение данных из очереди."""
    from app.rabbitmq import consume_response_from_queue

    return await consume_response_from_queue(correlation_id)


def validate_coefficients(
    response_data: dict[str, str] | None,
) -> tuple[Decimal, Decimal]:
    """Проверка и преобразование коэффициентов."""
    if response_data:
        coef_1st_team_win = response_data.get("coef_1st_team_win")
        coef_2nd_team_win = response_data.get("coef_2nd_team_win")

        if coef_1st_team_win is not None and coef_2nd_team_win is not None:
            try:
                return Decimal(coef_1st_team_win), Decimal(coef_2nd_team_win)
            except (ValueError, TypeError, InvalidOperation):
                logger.exception("Invalid value for coefficient")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid coefficient value provided.",
                )
        else:
            logger.error("Missing coefficients")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required coefficients for the event.",
            )
    else:
        logger.error("Response data is None")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event details.",
        )


async def insert_bet(
    session: AsyncSession,
    bet: BetCreate,
    coefficient: Decimal,
    possible_winning: Decimal,
) -> BetResponse:
    """Вставка ставки в базу данных."""
    try:
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

    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Database error occurred while creating bet")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    else:
        return BetResponse(**created_bet)


async def create_bet(bet: BetCreate, session: AsyncSession) -> BetResponse:
    correlation_id = str(uuid.uuid4())

    await send_bet_request(bet.event_id, correlation_id)

    response_data = await get_event_details(correlation_id)

    coef_1st_team_win, coef_2nd_team_win = validate_coefficients(response_data)

    coefficient = (
        coef_1st_team_win
        if bet.bet_prediction == "FIRST_TEAM_WIN"
        else coef_2nd_team_win
    )
    try:
        bet_amount = Decimal(bet.amount)
    except (ValueError, TypeError, InvalidOperation):
        logger.exception(f"Invalid bet amount: {bet.amount}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet amount provided.",
        )
    possible_winning = bet_amount * coefficient

    return await insert_bet(session, bet, coefficient, possible_winning)


async def get_all_bets(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
) -> list[BetResponse]:
    try:
        query = select(bets).offset(offset).limit(limit).order_by(bets.c.id)
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

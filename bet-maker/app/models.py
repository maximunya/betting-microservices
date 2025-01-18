from sqlalchemy import Column, Enum, Integer, Numeric, Table

from app.database import metadata
from app.schemas import BetPrediction, BetStatus

bets = Table(
    "bets",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("event_id", Integer, nullable=False),
    Column("bet_prediction", Enum(BetPrediction), nullable=False),
    Column("coefficient", Numeric(3, 2), nullable=False),
    Column("amount", Numeric(10, 2), nullable=False),
    Column("possible_winning", Numeric(15, 2), nullable=False),
    Column("status", Enum(BetStatus), default=BetStatus.NOT_PLAYED),
)

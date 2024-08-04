from datetime import datetime
from decimal import Decimal

from sqlalchemy import (TIMESTAMP, Column, Enum, Integer, MetaData, Numeric,
                        String, Table)

from .schemas import EventStatus

metadata = MetaData()

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String, nullable=False),
    Column("description", String),
    Column("coef_1st_team_win", Numeric(3, 2), nullable=False, default=Decimal("1.5")),
    Column("coef_2nd_team_win", Numeric(3, 2), nullable=False, default=Decimal("1.5")),
    Column("timestamp", TIMESTAMP(timezone=True), default=datetime.now, nullable=False),
    Column("deadline", TIMESTAMP(timezone=True), nullable=False),
    Column("status", Enum(EventStatus), default=EventStatus.NOT_FINISHED),
)

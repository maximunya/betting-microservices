from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class BetStatus(str, Enum):
    NOT_PLAYED = "NOT_PLAYED"
    WON = "WON"
    LOST = "LOST"


class BetPrediction(str, Enum):
    FIRST_TEAM_WIN = "FIRST_TEAM_WIN"
    SECOND_TEAM_WIN = "SECOND_TEAM_WIN"


class EventStatus(str, Enum):
    NOT_FINISHED = "NOT_FINISHED"
    FIRST_TEAM_WON = "FIRST_TEAM_WON"
    SECOND_TEAM_WON = "SECOND_TEAM_WON"


class BetCreate(BaseModel):
    event_id: int
    bet_prediction: BetPrediction
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class BetResponse(BaseModel):
    id: int
    event_id: int
    bet_prediction: BetPrediction
    coefficient: Decimal
    amount: Decimal
    possible_winning: Decimal
    status: BetStatus


class EventResponse(BaseModel):
    id: int
    name: str
    description: str
    coef_1st_team_win: Decimal
    coef_2nd_team_win: Decimal
    timestamp: datetime
    deadline: datetime
    status: EventStatus

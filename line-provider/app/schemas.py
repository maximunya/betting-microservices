from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    NOT_FINISHED = "NOT_FINISHED"
    FIRST_TEAM_WON = "FIRST_TEAM_WON"
    SECOND_TEAM_WON = "SECOND_TEAM_WON"


class EventCreate(BaseModel):
    name: str
    description: str | None = None
    coef_1st_team_win: Decimal = Field(Decimal("1.5"), gt=0, decimal_places=2)
    coef_2nd_team_win: Decimal = Field(Decimal("1.5"), gt=0, decimal_places=2)
    timestamp: datetime = Field(default_factory=datetime.now)
    deadline: datetime
    status: EventStatus = EventStatus.NOT_FINISHED


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    coef_1st_team_win: Decimal | None = Field(None, gt=0, decimal_places=2)
    coef_2nd_team_win: Decimal | None = Field(None, gt=0, decimal_places=2)
    deadline: datetime | None = None
    status: EventStatus | None = None


class EventResponse(BaseModel):
    id: int
    name: str
    description: str
    coef_1st_team_win: Decimal
    coef_2nd_team_win: Decimal
    timestamp: datetime
    deadline: datetime
    status: EventStatus

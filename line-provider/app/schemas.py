from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    NOT_FINISHED = "NOT_FINISHED"
    FIRST_TEAM_WON = "FIRST_TEAM_WON"
    SECOND_TEAM_WON = "SECOND_TEAM_WON"


class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    coef_1st_team_win: Decimal = Field(Decimal("1.5"), gt=0, decimal_places=2)
    coef_2nd_team_win: Decimal = Field(Decimal("1.5"), gt=0, decimal_places=2)
    timestamp: datetime = Field(default_factory=datetime.now)
    deadline: datetime
    status: EventStatus = EventStatus.NOT_FINISHED


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    coef_1st_team_win: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    coef_2nd_team_win: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    deadline: Optional[datetime] = None
    status: Optional[EventStatus] = None


class EventResponse(BaseModel):
    id: int
    name: str
    description: str
    coef_1st_team_win: Decimal
    coef_2nd_team_win: Decimal
    timestamp: datetime
    deadline: datetime
    status: EventStatus

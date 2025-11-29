from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StartRentalRequest(BaseModel):
    offer_id: UUID


class StartRentalResponse(BaseModel):
    rental_id: UUID
    started_at: datetime
    status: str


class FinishRentalRequest(BaseModel):
    station_id: str


class FinishRentalResponse(BaseModel):
    rental_id: UUID
    finished_at: datetime
    final_cost: float
    status: str

class RentalInfoResponse(BaseModel):
    rental_id: UUID
    status: str
    station_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    current_cost: float

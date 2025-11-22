from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

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

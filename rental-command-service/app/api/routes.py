from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rental_service import RentalService
from app.infrastructure.clients.offer_client import OfferClient
from app.infrastructure.clients.stations_adapter_client import StationsAdapter
from app.schemas import StartRentalRequest, StartRentalResponse, FinishRentalRequest, FinishRentalResponse
from app.api.dependencies import get_rental_command_service, get_user_id


router = APIRouter(prefix="/internal/rentals", tags=["rentals"])

@router.post("/start", response_model=StartRentalResponse)
async def start_rental(
    body: StartRentalRequest,
    user_id: UUID = Depends(get_user_id),
    service: RentalService = Depends(get_rental_command_service)
):
    try:
        rental = await service.start_rental(user_id, body.offer_id)
        
        return StartRentalResponse(
            rental_id=rental.rental_id,
            started_at=rental.started_at,
            status=rental.status.value
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rental_id}/finish", response_model=FinishRentalResponse)
async def finish_rental(
    rental_id: UUID,
    body: FinishRentalRequest,
    user_id: UUID = Depends(get_user_id),
    service: RentalService = Depends(get_rental_command_service)
):
    
    try:
        res = await service.finish_rental(user_id, rental_id, body.station_id)
        
        return FinishRentalResponse(
            rental_id=res["rental_id"],
            finished_at=res["finished_at"],
            final_cost=res["final_cost"],
            status="FINISHED"
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

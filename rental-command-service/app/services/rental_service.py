
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from dateutil import parser
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repository import RentalRepository
from app.infrastructure.clients.offer_client import OfferClient
from app.infrastructure.clients.stations_adapter_client import StationsAdapter
from app.domain.exception import (
    OfferNotActiveException,
    ExpireAtNotFoundException,
    UserAlreadyRentException,
    OfferNotBelongUserException,
    OfferExpiredException,
    RentalNotFoundException,
    UserIdsMismatchException,
    RentalAlreadyFinishedException,
    StationIdMissedException,
)
from app.utils import now, minutes_between


class RentalService:
    def __init__(self, session: AsyncSession, offer_client: OfferClient, stations_adapter: StationsAdapter):
        self.session = session
        self.repo = RentalRepository(session)
        self.offer_client = offer_client
        self.stations_adapter = stations_adapter

    async def start_rental(self, user_id: UUID, offer_id: UUID):
        try:
            async with self.session.begin():
                offer = await self.offer_client.get_offer(str(offer_id))
                
                if offer.get("status") != "ACTIVE":
                    print("NOT ACTIVE")
                    raise OfferNotActiveException(str(offer_id))

                expires_at = offer.get("expires_at")
                if not expires_at:
                    print("2")
                    raise ExpireAtNotFoundException(str(offer_id))

                existing_rental = await self.repo.get_by_user_id(user_id)
                if existing_rental:
                    print("3")
                    raise UserAlreadyRentException(str(user_id), str(offer_id))

                if offer.get("user_id") != str(user_id):
                    print("4")
                    raise OfferNotBelongUserException(str(user_id), str(offer_id))

                expires_dt = parser.isoparse(expires_at)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)

                if expires_dt < datetime.now(timezone.utc):
                    print("5")
                    raise OfferExpiredException(str(offer_id))

                station_id = offer.get("station_id")
                if not station_id:
                    print("6")
                    raise StationIdMissedException(str(offer_id))

                existing_offer_rental = await self.repo.get_by_offer_id_active(offer_id)
                if existing_offer_rental:
                    print("7")
                    return existing_offer_rental

                st_resp = await self.stations_adapter.reserve_or_issue(
                    station_id=station_id, user_id=str(user_id)
                )

                rental = await self.repo.create_rental(
                    offer_id=offer_id,
                    user_id=user_id,
                    station_id=station_id,
                    tariff_snapshot=offer.get("tariff_snapshot") or {},
                    tariff_version=offer.get("tariff_version")
                )

                await self.repo.insert_event(
                    rental.rental_id,
                    "rental_started",
                    {"station_response": st_resp}
                )

                return rental

        except (
            OfferNotActiveException,
            ExpireAtNotFoundException,
            UserAlreadyRentException,
            OfferNotBelongUserException,
            OfferExpiredException,
            StationIdMissedException
        ) as e:
            raise

    

    async def finish_rental(self, user_id: UUID, rental_id: UUID, return_station_id: str):
        try:
            async with self.session.begin():
                rental = await self.repo.get(rental_id)
                if not rental:
                    raise RentalNotFoundException(str(user_id), str(rental_id), return_station_id)

                if str(rental.user_id) != str(user_id):
                    raise UserIdsMismatchException(str(rental.user_id), str(user_id))

                if rental.status == "FINISHED":
                    raise RentalAlreadyFinishedException(str(user_id), str(rental_id))

                started = rental.started_at
                finished = datetime.now(timezone.utc)
                tariff = rental.tariff_snapshot or {}
                initial_fee = Decimal(str(tariff.get("initial_fee", 0)))
                per_minute = Decimal(str(tariff.get("per_minute", 0)))
                mins = minutes_between(started, finished)
                total = initial_fee + (per_minute * Decimal(mins))

                st_resp = await self.stations_adapter.return_powerbank(
                    station_id=return_station_id,
                    rental_id=str(rental_id)
                )

                await self.repo.finish_rental(rental_id, finished, total)

                await self.repo.insert_event(
                    rental_id,
                    "rental_finished",
                    {"station_response": st_resp, "calculated_minutes": mins}
                )

                outbox = await self.repo.create_outbox_payment(
                    rental_id=rental_id,
                    amount=total
                )

                return {
                    "rental_id": rental_id,
                    "finished_at": finished,
                    "final_cost": float(total),
                    "outbox_id": outbox.id
                }

        except (
            RentalNotFoundException,
            UserIdsMismatchException,
            RentalAlreadyFinishedException
        ) as e:
            raise

import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"
TEST_OFFER_ID = "987e6543-e21b-12d3-a456-426614174000"
TEST_STATION_ID = "test-station-id"

USER_SERVICE_URL="http://localhost:8001"
OFFER_SERVICE_URL="http://localhost:8002"
RENTAL_SERVICE_URL="http://localhost:8003"

@pytest.mark.asyncio
async def test_start_rental_integration():
    
    async with AsyncClient(base_url=OFFER_SERVICE_URL) as ac:
        offer = await ac.post(
            "/internal/offers",
            json={
                "user_id": TEST_USER_ID,
                "station_id": TEST_STATION_ID
            },
            headers={"Content-Type": "application/json"}
        )
    print(offer)
    offer_data = offer.json() 
    print(offer_data)
    
    async with AsyncClient(base_url=RENTAL_SERVICE_URL) as ac:
        response = await ac.post(
            "/internal/rentals/start",
            headers={"Authorization": f"Bearer {TEST_USER_ID}"},
            json={"offer_id": offer_data['offer_id']},
        )
    print(response)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    print(data)
    assert "rental_id" in data
    assert data["status"] == "ACTIVE"

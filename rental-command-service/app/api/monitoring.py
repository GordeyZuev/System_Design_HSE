from fastapi import APIRouter
from starlette.responses import Response

router = APIRouter(tags=["monitoring"])

@router.get("/health")
async def health():
    return {"status": "ok"}


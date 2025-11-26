from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.responses import Response


router = APIRouter(tags=["monitoring"])


@app.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
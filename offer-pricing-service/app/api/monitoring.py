"""Monitoring endpoints."""
from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.responses import Response

router = APIRouter(tags=["monitoring"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


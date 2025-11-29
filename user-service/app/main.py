"""Main application entry point."""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import bcrypt
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import dependencies, monitoring, routes
from app.domain.models import (
    User,
    UserProfile,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure standard logging
logging.basicConfig(
    format="%(message)s",
    level=getattr(logging, settings.log_level.upper()),
)

logger = logging.getLogger(__name__)


async def init_test_users() -> None:
    """Initialize test users in in-memory storage."""
    user_repo = dependencies.get_user_repository()
    profile_repo = dependencies.get_user_profile_repository()
    segment_repo = dependencies.get_user_segment_repository()

    password = "testpassword123"
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    segments = [UserSegment.STANDARD, UserSegment.PREMIUM, UserSegment.VIP]

    for i in range(1, 6):
        email = f"test{i}@example.com"
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            continue

        user = User(
            email=email,
            phone=f"+123456789{i}",
            password_hash=password_hash,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        created_user = await user_repo.create(user)

        profile = UserProfile(
            user_id=created_user.user_id,
            name=f"Test User {i}",
            extra_metadata_json={},
        )
        await profile_repo.create(profile)

        segment_type = segments[(i - 1) % len(segments)]
        segment = UserSegmentModel(
            user_id=created_user.user_id,
            segment=segment_type,
            updated_at=datetime.now(timezone.utc),
        )
        await segment_repo.create(segment)

        logger.info(f"Test user {i} initialized: {email} ({segment_type.value})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("Using in-memory database")
    await init_test_users()
    yield
    logger.info("Shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="User Service (Auth & Profile) for Powerbank Rental System",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.auth_router)
app.include_router(routes.users_router)
app.include_router(monitoring.router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "storage": "in-memory",
    }


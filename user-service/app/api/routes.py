"""API routes."""
import logging
from datetime import datetime, timezone
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from prometheus_client import Counter, Histogram

from app.domain.exceptions import (
    DomainException,
    InvalidCredentialsException,
    InvalidTokenException,
    RefreshTokenNotFoundException,
    RefreshTokenRevokedException,
    TokenExpiredException,
    UserNotFoundException,
)
from app.domain.models import (
    JWTValidateRequest,
    JWTValidateResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    User,
    UserProfile,
    UserSegment,
    UserSegmentModel,
    UserStatus,
)
from app.infrastructure.jwt_handler import JWTHandler
from app.services.auth_service import AuthService
from app.services.user_service import UserService

from .dependencies import (
    get_auth_service,
    get_jwt_handler,
    get_user_profile_repository,
    get_user_repository,
    get_user_segment_repository,
    get_user_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth", "users"])
dev_router = APIRouter(tags=["dev"], prefix="/dev")

# Prometheus metrics
login_counter = Counter(
    "auth_login_total", "Total number of login attempts", ["status"]
)
refresh_counter = Counter(
    "auth_refresh_total", "Total number of token refresh attempts", ["status"]
)
user_get_counter = Counter(
    "user_get_total", "Total number of user info retrievals", ["status"]
)
jwt_validate_counter = Counter(
    "jwt_validate_total", "Total number of JWT validations", ["status"]
)
login_duration = Histogram(
    "auth_login_duration_seconds", "Time spent on login"
)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Login endpoint."""
    try:
        with login_duration.time():
            response = await service.login(request)
        login_counter.labels(status="success").inc()
        return response
    except InvalidCredentialsException as e:
        logger.warning(f"Login failed: {e.message}")
        login_counter.labels(status="invalid_credentials").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    except DomainException as e:
        logger.error(f"Domain error during login: {e}")
        login_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        login_counter.labels(status="internal_error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )


@router.post(
    "/auth/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK
)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    """Refresh token endpoint."""
    try:
        response = await service.refresh(request)
        refresh_counter.labels(status="success").inc()
        return response
    except (
        RefreshTokenNotFoundException,
        RefreshTokenRevokedException,
        InvalidTokenException,
        TokenExpiredException,
    ) as e:
        logger.warning(f"Refresh failed: {e.message}")
        refresh_counter.labels(status="invalid_token").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    except DomainException as e:
        logger.error(f"Domain error during refresh: {e}")
        refresh_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error during refresh: {e}")
        refresh_counter.labels(status="internal_error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )


@router.get("/api/v1/users/{user_id}")
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Get user information."""
    try:
        user_info = await service.get_user_info(user_id)
        user_get_counter.labels(status="success").inc()
        return {
            "user_id": str(user_info.user_id),
            "email": user_info.email,
            "segment": user_info.segment.value,
            "status": user_info.status,
            "phone": user_info.phone,
        }
    except UserNotFoundException as e:
        logger.warning(f"User not found: {e.message}")
        user_get_counter.labels(status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.exception(f"Unexpected error getting user: {e}")
        user_get_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )


@router.post("/api/v1/jwt/validate", response_model=JWTValidateResponse)
async def validate_jwt(
    request: JWTValidateRequest,
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
) -> JWTValidateResponse:
    """Validate JWT token."""
    try:
        payload = jwt_handler.validate_access_token(request.token)
        jwt_validate_counter.labels(status="valid").inc()
        return JWTValidateResponse(
            valid=True,
            user_id=UUID(payload["sub"]),
            segment=payload.get("segment"),
            roles=payload.get("roles", []),
        )
    except (TokenExpiredException, InvalidTokenException) as e:
        logger.warning(f"JWT validation failed: {e.message}")
        jwt_validate_counter.labels(status="invalid").inc()
        return JWTValidateResponse(valid=False)
    except Exception as e:
        logger.exception(f"Unexpected error validating JWT: {e}")
        jwt_validate_counter.labels(status="error").inc()
        return JWTValidateResponse(valid=False)


@dev_router.post("/create-test-user")
async def create_test_user(
    user_repo=Depends(get_user_repository),
    profile_repo=Depends(get_user_profile_repository),
    segment_repo=Depends(get_user_segment_repository),
) -> dict:
    """Create test user for development/testing."""
    try:
        existing_user = await user_repo.get_by_email("test@example.com")
        if existing_user:
            return {
                "message": "Test user already exists",
                "user_id": str(existing_user.user_id),
                "email": existing_user.email,
            }

        password = "testpassword123"
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        user = User(
            email="test@example.com",
            phone="+1234567890",
            password_hash=password_hash,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        created_user = await user_repo.create(user)

        profile = UserProfile(
            user_id=created_user.user_id,
            name="Test User",
            extra_metadata_json={},
        )
        await profile_repo.create(profile)

        segment = UserSegmentModel(
            user_id=created_user.user_id,
            segment=UserSegment.STANDARD,
            updated_at=datetime.now(timezone.utc),
        )
        await segment_repo.create(segment)

        logger.info(f"Test user created: {created_user.user_id}")

        return {
            "message": "Test user created successfully",
            "user_id": str(created_user.user_id),
            "email": "test@example.com",
            "password": "testpassword123",
            "segment": "STANDARD",
        }
    except Exception as e:
        logger.exception(f"Failed to create test user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)},
        )


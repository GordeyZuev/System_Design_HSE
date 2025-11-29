"""API dependencies."""
from typing import Optional

from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.repositories_inmemory import (
    InMemoryRefreshTokenRepository,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
    InMemoryUserSegmentRepository,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

# Singleton instances
_user_repository: Optional[InMemoryUserRepository] = None
_user_profile_repository: Optional[InMemoryUserProfileRepository] = None
_user_segment_repository: Optional[InMemoryUserSegmentRepository] = None
_refresh_token_repository: Optional[InMemoryRefreshTokenRepository] = None
_jwt_handler: Optional[JWTHandler] = None


def get_user_repository() -> InMemoryUserRepository:
    """Get UserRepository singleton."""
    global _user_repository
    if _user_repository is None:
        _user_repository = InMemoryUserRepository()
    return _user_repository


def get_user_profile_repository() -> InMemoryUserProfileRepository:
    """Get UserProfileRepository singleton."""
    global _user_profile_repository
    if _user_profile_repository is None:
        _user_profile_repository = InMemoryUserProfileRepository()
    return _user_profile_repository


def get_user_segment_repository() -> InMemoryUserSegmentRepository:
    """Get UserSegmentRepository singleton."""
    global _user_segment_repository
    if _user_segment_repository is None:
        _user_segment_repository = InMemoryUserSegmentRepository()
    return _user_segment_repository


def get_refresh_token_repository() -> InMemoryRefreshTokenRepository:
    """Get RefreshTokenRepository singleton."""
    global _refresh_token_repository
    if _refresh_token_repository is None:
        _refresh_token_repository = InMemoryRefreshTokenRepository()
    return _refresh_token_repository


def get_jwt_handler() -> JWTHandler:
    """Get JWTHandler singleton."""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler


def get_auth_service() -> AuthService:
    """Get AuthService with dependencies."""
    return AuthService(
        user_repository=get_user_repository(),
        user_segment_repository=get_user_segment_repository(),
        refresh_token_repository=get_refresh_token_repository(),
        jwt_handler=get_jwt_handler(),
    )


def get_user_service() -> UserService:
    """Get UserService with dependencies."""
    return UserService(
        user_repository=get_user_repository(),
        user_profile_repository=get_user_profile_repository(),
        user_segment_repository=get_user_segment_repository(),
    )


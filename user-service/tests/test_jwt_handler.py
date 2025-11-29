"""Tests for JWT Handler."""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.domain.exceptions import InvalidTokenException, TokenExpiredException
from app.domain.models import UserSegment
from app.infrastructure.jwt_handler import JWTHandler


@pytest.fixture
def jwt_handler() -> JWTHandler:
    """JWT handler fixture."""
    return JWTHandler(secret="test-secret-key")


@pytest.fixture
def mock_user_id() -> UUID:
    """Mock user ID."""
    return UUID("12345678-1234-5678-1234-567812345678")


def test_create_access_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test creating access token."""
    token = jwt_handler.create_access_token(
        mock_user_id, UserSegment.STANDARD
    )

    assert token is not None
    assert len(token) > 0

    payload = jwt.decode(
        token, jwt_handler.secret, algorithms=[jwt_handler.algorithm]
    )
    assert payload["sub"] == str(mock_user_id)
    assert payload["segment"] == "STANDARD"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload
    assert "roles" in payload
    assert payload["roles"] == ["user"]


def test_create_access_token_with_custom_roles(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test creating access token with custom roles."""
    roles = ["user", "admin"]
    token = jwt_handler.create_access_token(
        mock_user_id, UserSegment.PREMIUM, roles=roles
    )
    
    payload = jwt.decode(token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
    assert payload["roles"] == roles
    assert payload["segment"] == "PREMIUM"


def test_create_access_token_with_custom_expiry(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test creating access token with custom expiry."""
    token = jwt_handler.create_access_token(
        mock_user_id, UserSegment.STANDARD, expires_in_minutes=30
    )
    
    payload = jwt.decode(token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
    exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
    iat_time = datetime.fromtimestamp(payload["iat"], timezone.utc)
    
    # Should be approximately 30 minutes
    diff = exp_time - iat_time
    assert 29 <= diff.total_seconds() / 60 <= 31


def test_create_refresh_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test creating refresh token."""
    token = jwt_handler.create_refresh_token(mock_user_id)
    
    assert token is not None
    assert len(token) > 0
    
    # Decode and verify
    payload = jwt.decode(token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
    assert payload["sub"] == str(mock_user_id)
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_validate_token_success(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test validating valid token."""
    token = jwt_handler.create_access_token(mock_user_id, UserSegment.STANDARD)
    payload = jwt_handler.validate_token(token)
    
    assert payload["sub"] == str(mock_user_id)
    assert payload["segment"] == "STANDARD"


def test_validate_token_invalid(jwt_handler: JWTHandler) -> None:
    """Test validating invalid token."""
    with pytest.raises(InvalidTokenException):
        jwt_handler.validate_token("invalid-token")


def test_validate_token_wrong_secret(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test validating token with wrong secret."""
    # Create token with one secret
    token = jwt_handler.create_access_token(mock_user_id, UserSegment.STANDARD)
    
    # Try to validate with different secret
    other_handler = JWTHandler(secret="different-secret")
    with pytest.raises(InvalidTokenException):
        other_handler.validate_token(token)


def test_validate_token_expired(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test validating expired token."""
    # Create expired token manually
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(mock_user_id),
        "segment": "STANDARD",
        "roles": ["user"],
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=1),  # Expired 1 minute ago
        "type": "access",
    }
    expired_token = jwt.encode(payload, jwt_handler.secret, algorithm=jwt_handler.algorithm)
    
    with pytest.raises(TokenExpiredException):
        jwt_handler.validate_token(expired_token)


def test_validate_access_token_success(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test validating access token."""
    token = jwt_handler.create_access_token(mock_user_id, UserSegment.STANDARD)
    payload = jwt_handler.validate_access_token(token)
    
    assert payload["type"] == "access"
    assert payload["sub"] == str(mock_user_id)


def test_validate_access_token_with_refresh_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test validating refresh token as access token should fail."""
    refresh_token = jwt_handler.create_refresh_token(mock_user_id)
    
    with pytest.raises(InvalidTokenException) as exc_info:
        jwt_handler.validate_access_token(refresh_token)
    
    assert "not an access token" in str(exc_info.value).lower()


def test_get_user_id_from_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test extracting user ID from token."""
    token = jwt_handler.create_access_token(mock_user_id, UserSegment.STANDARD)
    user_id = jwt_handler.get_user_id_from_token(token)
    
    assert user_id == mock_user_id


def test_get_segment_from_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test extracting segment from token."""
    token = jwt_handler.create_access_token(mock_user_id, UserSegment.VIP)
    segment = jwt_handler.get_segment_from_token(token)
    
    assert segment == UserSegment.VIP


def test_get_roles_from_token(jwt_handler: JWTHandler, mock_user_id: UUID) -> None:
    """Test extracting roles from token."""
    roles = ["user", "admin", "moderator"]
    token = jwt_handler.create_access_token(
        mock_user_id, UserSegment.PREMIUM, roles=roles
    )
    extracted_roles = jwt_handler.get_roles_from_token(token)
    
    assert extracted_roles == roles




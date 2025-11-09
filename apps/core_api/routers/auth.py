"""
Authentication Router.

Endpoints:
- POST /auth/token - Create access + refresh tokens
- POST /auth/refresh - Exchange refresh token for new access token
- POST /auth/revoke - Revoke access and/or refresh tokens
- GET /auth/me - Get current user info

Agent: authentication-authorization/security-auditor
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from apps.core_api.auth import (
    TokenResponse,
    User,
    blacklist_token,
    create_access_token,
    generate_jwt_token,
)
from apps.core_api.deps import get_current_user
from chad_config.settings import Settings
from jose import JWTError, jwt

settings = Settings()
router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class TokenRequest(BaseModel):
    """Request model for token creation."""

    user_id: str
    password: str | None = None  # Optional: for future password auth
    scopes: list[str] = []


class RefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class RevokeRequest(BaseModel):
    """Request model for token revocation."""

    access_token: str | None = None
    refresh_token: str | None = None


class UserResponse(BaseModel):
    """Response model for user info."""

    user_id: str
    scopes: list[str]


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/token", response_model=TokenResponse)
async def create_token(request: TokenRequest) -> TokenResponse:
    """
    Create access and refresh tokens.

    Note: This is a simplified implementation for development.
    In production, validate user credentials (password, OAuth, etc.)
    before issuing tokens.

    Args:
        request: Token creation request

    Returns:
        TokenResponse: Access and refresh tokens

    Example:
        POST /auth/token
        {
            "user_id": "user_123",
            "scopes": ["notion.*", "github.read"]
        }
    """
    # TODO: In production, validate credentials here
    # For now, we trust the caller and issue tokens

    return generate_jwt_token(request.user_id, request.scopes)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request

    Returns:
        TokenResponse: New access token (no new refresh token)

    Raises:
        HTTPException: 401 if refresh token is invalid or revoked

    Example:
        POST /auth/refresh
        {
            "refresh_token": "eyJhbGc..."
        }
    """
    try:
        # Decode and validate refresh token
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Verify it's a refresh token
        token_type = payload.get("token_type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected refresh token.",
            )

        # Check if token is blacklisted
        from apps.core_api.auth import is_token_blacklisted

        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Extract user info
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
            )

        # Fetch scopes from database or use default
        # TODO: Fetch from database
        scopes = payload.get("scopes", [])

        # Generate new access token
        access_token = create_access_token(user_id, scopes)

        return TokenResponse(
            access_token=access_token,
            refresh_token=None,  # Don't issue new refresh token
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        ) from e


@router.post("/revoke")
async def revoke_tokens(request: RevokeRequest) -> dict:
    """
    Revoke access and/or refresh tokens.

    Args:
        request: Revocation request with tokens to revoke

    Returns:
        dict: Revocation status

    Example:
        POST /auth/revoke
        {
            "access_token": "eyJhbGc...",
            "refresh_token": "eyJhbGc..."
        }
    """
    revoked = []

    if request.access_token:
        await blacklist_token(request.access_token)
        revoked.append("access_token")

    if request.refresh_token:
        await blacklist_token(request.refresh_token)
        revoked.append("refresh_token")

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tokens provided for revocation",
        )

    return {
        "status": "revoked",
        "tokens": revoked,
        "message": f"Successfully revoked {len(revoked)} token(s)",
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        user: Current user (from JWT)

    Returns:
        UserResponse: User info

    Example:
        GET /auth/me
        Authorization: Bearer eyJhbGc...
    """
    return UserResponse(user_id=user.user_id, scopes=user.scopes)


# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ authentication-authorization/security-auditor

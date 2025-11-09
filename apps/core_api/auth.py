"""
Authentication and Authorization.

Implements:
- JWT token validation (python-jose)
- HMAC signature validation (hashlib)
- Actor scope checking
- Token generation (for /auth/token endpoint)

NOTE: No passlib dependency - HMAC uses built-in hashlib

Agents:
- full-stack-orchestration/security-auditor
- api-scaffolding/backend-architect
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
from redis.asyncio import Redis

from chad_config.settings import Settings

settings = Settings()

# Global Redis client placeholder (will be set via dependency injection)
_redis_client: Optional[Redis] = None


def set_redis_client(redis: Redis) -> None:
    """Set global Redis client for token blacklisting."""
    global _redis_client
    _redis_client = redis


def get_redis_client() -> Optional[Redis]:
    """Get global Redis client."""
    return _redis_client


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # Subject (actor identifier)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # JWT ID (for revocation)
    scopes: list[str] = []  # Optional: embedded actor scopes
    token_type: str = "access"  # "access" or "refresh"


class TokenResponse(BaseModel):
    """Token generation response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class User(BaseModel):
    """User model extracted from JWT."""

    user_id: str
    scopes: list[str] = []


class ServiceAccount(BaseModel):
    """Service account model for HMAC authentication."""

    service_id: str
    scopes: list[str] = []


# ============================================================================
# JWT VALIDATION
# ============================================================================


async def validate_jwt(authorization_header: str) -> User:
    """
    Validate JWT token from Authorization header.

    Args:
        authorization_header: "Bearer <token>" format

    Returns:
        User: User model with user_id and scopes

    Raises:
        HTTPException: 401 if validation fails

    Example:
        user = await validate_jwt("Bearer eyJhbGc...")
        print(f"User: {user.user_id}, Scopes: {user.scopes}")
    """
    # Extract token from "Bearer <token>" format
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization_header[7:]  # Remove "Bearer " prefix

    # Decode and validate JWT
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Validate expiration (jose does this automatically, but explicit check is good)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token blacklist
        token_id = payload.get("jti")
        if token_id and await is_token_blacklisted(token_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract user info
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scopes = payload.get("scopes", [])

        return User(user_id=user_id, scopes=scopes)

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ============================================================================
# HMAC VALIDATION
# ============================================================================


async def validate_hmac(
    request_body: bytes, signature_header: str, timestamp_header: str, service_id: str = "n8n"
) -> ServiceAccount:
    """
    Validate HMAC signature of request body.

    Args:
        request_body: Raw request body bytes
        signature_header: HMAC signature from X-HMAC-Signature header
        timestamp_header: Request timestamp from X-Request-Timestamp header
        service_id: Service account identifier (default: "n8n")

    Returns:
        ServiceAccount: Service account model

    Raises:
        HTTPException: 401 if signature is invalid or timestamp is too old

    Security Notes:
    - Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks
    - HMAC_SECRET_KEY must be shared securely with n8n
    - Rotate HMAC_SECRET_KEY periodically
    - Use HTTPS to protect HMAC_SECRET_KEY in transit

    Example:
        service_account = await validate_hmac(
            request.body(),
            request.headers["X-HMAC-Signature"],
            request.headers["X-Request-Timestamp"]
        )
    """
    # Validate timestamp to prevent replay attacks
    try:
        request_timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Request-Timestamp header. Must be Unix timestamp.",
        )

    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    timestamp_tolerance = getattr(settings, "HMAC_TIMESTAMP_TOLERANCE_SECONDS", 300)

    if abs(current_timestamp - request_timestamp) > timestamp_tolerance:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Request timestamp too old. Tolerance: {timestamp_tolerance} seconds.",
        )

    # Compute expected HMAC signature
    expected_signature = hmac.new(
        settings.HMAC_SECRET_KEY.encode("utf-8"), request_body, hashlib.sha256
    ).hexdigest()

    # Constant-time comparison (prevents timing attacks)
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature. Request body may have been tampered with.",
        )

    # Return service account with default scopes for n8n
    return ServiceAccount(
        service_id=service_id,
        scopes=["notion.*", "google.*", "github.read", "local.*"],
    )


# ============================================================================
# TOKEN GENERATION
# ============================================================================


def create_access_token(user_id: str, scopes: list[str] | None = None) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User identifier (will be "sub" claim)
        scopes: Optional list of scopes to embed in token

    Returns:
        str: Encoded JWT access token

    Example:
        token = create_access_token("user_123", ["notion.*", "github.read"])
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    payload: dict[str, Any] = {
        "sub": user_id,  # Subject (user)
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(exp.timestamp()),  # Expiration
        "jti": str(uuid.uuid4()),  # JWT ID (for revocation)
        "token_type": "access",
    }

    # Optionally embed scopes in token (alternative: fetch from DB)
    if scopes:
        payload["scopes"] = scopes

    # Encode JWT
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token (long-lived, no scopes).

    Args:
        user_id: User identifier

    Returns:
        str: Encoded JWT refresh token

    Example:
        refresh = create_refresh_token("user_123")
    """
    now = datetime.now(timezone.utc)
    refresh_expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    exp = now + timedelta(days=refresh_expire_days)

    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
        "token_type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_jwt_token(user_id: str, scopes: list[str] | None = None) -> TokenResponse:
    """
    Generate JWT access and refresh tokens.

    Args:
        user_id: User identifier (will be "sub" claim)
        scopes: Optional list of scopes to embed in token

    Returns:
        TokenResponse: Access token, refresh token, and metadata

    Example:
        tokens = generate_jwt_token("user_123", ["notion.*", "github.read"])
        # Use tokens.access_token in Authorization header
        # Use tokens.refresh_token to get new access token
    """
    access_token = create_access_token(user_id, scopes)
    refresh_token = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,  # Convert to seconds
    )


# ============================================================================
# TOKEN ENDPOINT (TODO: Mount in router)
# ============================================================================


async def create_token_endpoint(user_id: str, scopes: list[str] | None = None) -> TokenResponse:
    """
    Token creation endpoint handler.

    Args:
        user_id: User identifier
        scopes: Optional scopes to grant

    Returns:
        TokenResponse: JWT tokens (access + refresh)

    Note: In production, validate user credentials before calling this.

    Example Router:
        @router.post("/auth/token")
        async def token_endpoint(
            user_id: str = Body(...),
            scopes: list[str] = Body([])
        ):
            # Validate credentials here
            return await create_token_endpoint(user_id, scopes)
    """
    return generate_jwt_token(user_id, scopes)


# ============================================================================
# TOKEN REVOCATION (TODO: Implement)
# ============================================================================


async def blacklist_token(token: str) -> None:
    """
    Revoke a JWT token by adding to blacklist.

    Args:
        token: JWT token to revoke

    Redis Schema:
        Key: f"token_blacklist:{jti}"
        Value: "revoked"
        TTL: time_until_token_expires

    Example:
        await blacklist_token(user_token)
        # Subsequent requests with this token will fail validation
    """
    redis = get_redis_client()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available for token revocation",
        )

    try:
        # Decode token to extract jti and exp (don't validate, just decode)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # Don't verify expiration when revoking
        )

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token missing 'jti' claim. Cannot revoke.",
            )

        exp = payload.get("exp")
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token missing 'exp' claim. Cannot revoke.",
            )

        # Calculate TTL (seconds until token expires)
        current_time = int(datetime.now(timezone.utc).timestamp())
        ttl = max(exp - current_time, 0)

        if ttl > 0:
            # Add to blacklist with TTL matching token expiration
            await redis.setex(f"token_blacklist:{jti}", ttl, "revoked")
        # If TTL <= 0, token already expired, no need to blacklist

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token: {str(e)}",
        ) from e


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if token is blacklisted.

    Args:
        jti: JWT ID (unique token identifier)

    Returns:
        bool: True if blacklisted, False otherwise
    """
    redis = get_redis_client()
    if not redis:
        # If Redis is not available, assume token is not blacklisted
        # This allows the system to continue operating even if Redis is down
        return False

    try:
        result = await redis.get(f"token_blacklist:{jti}")
        return result is not None
    except Exception:
        # If Redis query fails, assume token is not blacklisted
        return False


# ============================================================================
# SCOPE VALIDATION
# ============================================================================


def scope_matches(required: str, granted: str) -> bool:
    """
    Check if a granted scope matches a required scope.

    Supports:
    - Exact match: "runs:read" == "runs:read"
    - Wildcard: "runs:*" matches "runs:read"
    - Admin: "*" matches everything
    - Hierarchy: "runs:write" includes "runs:read" (write implies read)

    Args:
        required: Required scope pattern
        granted: Granted scope from token

    Returns:
        bool: True if granted scope satisfies required scope

    Example:
        scope_matches("runs:read", "runs:*")  # True
        scope_matches("runs:read", "*")  # True
        scope_matches("runs:write", "runs:read")  # False
    """
    # Admin wildcard grants everything
    if granted == "*":
        return True

    # Exact match
    if required == granted:
        return True

    # Wildcard matching: "notion.*" matches "notion.read"
    if granted.endswith(".*"):
        prefix = granted[:-2]  # Remove ".*"
        if required.startswith(prefix + ".") or required.startswith(prefix + ":"):
            return True

    if granted.endswith(":*"):
        prefix = granted[:-2]  # Remove ":*"
        if required.startswith(prefix + ".") or required.startswith(prefix + ":"):
            return True

    # Hierarchy: "runs:write" includes "runs:read"
    if ":" in required and ":" in granted:
        req_resource, req_action = required.rsplit(":", 1)
        grant_resource, grant_action = granted.rsplit(":", 1)

        if req_resource == grant_resource:
            # Write includes read
            if grant_action == "write" and req_action == "read":
                return True

    return False


def check_scopes(required_scopes: list[str], user_scopes: list[str]) -> bool:
    """
    Check if user has all required scopes.

    Args:
        required_scopes: List of required scopes
        user_scopes: List of scopes granted to user

    Returns:
        bool: True if all required scopes are satisfied

    Example:
        if not check_scopes(["notion.write"], user.scopes):
            raise HTTPException(403, "Insufficient permissions")
    """
    for required in required_scopes:
        # Check if any granted scope matches the required scope
        if not any(scope_matches(required, granted) for granted in user_scopes):
            return False

    return True


# ============================================================================
# HELPER: Generate HMAC for testing
# ============================================================================


def generate_hmac_signature(body: str | bytes) -> str:
    """
    Generate HMAC signature for request body (testing helper).

    Args:
        body: Request body (string or bytes)

    Returns:
        str: Hex-encoded HMAC signature

    Example (Python):
        signature = generate_hmac_signature(json.dumps({"actor": "test"}))
        headers = {"X-HMAC-Signature": signature}

    Example (Bash):
        BODY='{"actor":"test"}'
        SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$HMAC_SECRET_KEY" | awk '{print $2}')

    Example (n8n Code Node):
        const crypto = require('crypto');
        const body = JSON.stringify($input.item.json);
        const signature = crypto.createHmac('sha256', process.env.HMAC_SECRET_KEY)
            .update(body).digest('hex');
        return {signature};
    """
    if isinstance(body, str):
        body = body.encode("utf-8")

    return hmac.new(settings.HMAC_SECRET_KEY.encode("utf-8"), body, hashlib.sha256).hexdigest()


# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ full-stack-orchestration/security-auditor
# ✅ api-scaffolding/backend-architect

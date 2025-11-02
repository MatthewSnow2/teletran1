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
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from chad_config.settings import Settings

settings = Settings()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # Subject (actor identifier)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    scopes: list[str] = []  # Optional: embedded actor scopes


class TokenResponse(BaseModel):
    """Token generation response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


# ============================================================================
# JWT VALIDATION
# ============================================================================


async def validate_jwt(authorization_header: str) -> dict[str, Any]:
    """
    Validate JWT token from Authorization header.

    Args:
        authorization_header: "Bearer <token>" format

    Returns:
        dict: Decoded JWT payload

    Raises:
        HTTPException: 401 if validation fails

    TODO: Add token blacklist check (Redis)
    TODO: Add token refresh logic
    TODO: Add audience (aud) claim validation
    TODO: Add issuer (iss) claim validation

    Example:
        payload = await validate_jwt("Bearer eyJhbGc...")
        actor = payload["sub"]
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
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # TODO: Check token blacklist
        # token_id = payload.get("jti")
        # if token_id and await is_token_blacklisted(token_id):
        #     raise HTTPException(status_code=401, detail="Token has been revoked")

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ============================================================================
# HMAC VALIDATION
# ============================================================================


async def validate_hmac(request_body: bytes, signature_header: str) -> None:
    """
    Validate HMAC signature of request body.

    Args:
        request_body: Raw request body bytes
        signature_header: HMAC signature from X-HMAC-Signature header

    Raises:
        HTTPException: 401 if signature is invalid

    Security Notes:
    - Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks
    - HMAC_SECRET_KEY must be shared securely with n8n
    - Rotate HMAC_SECRET_KEY periodically
    - Use HTTPS to protect HMAC_SECRET_KEY in transit

    Example:
        await validate_hmac(request.body(), request.headers["X-HMAC-Signature"])
    """
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


# ============================================================================
# TOKEN GENERATION
# ============================================================================


def generate_jwt_token(actor: str, scopes: list[str] | None = None) -> TokenResponse:
    """
    Generate JWT token for actor.

    Args:
        actor: Actor identifier (will be "sub" claim)
        scopes: Optional list of scopes to embed in token

    Returns:
        TokenResponse: Access token and metadata

    TODO: Add refresh token generation
    TODO: Add "jti" (JWT ID) for blacklisting support
    TODO: Add "aud" (audience) and "iss" (issuer) claims

    Example:
        token = generate_jwt_token("user_123", ["notion.*", "github.read"])
        # Use token.access_token in Authorization header
    """
    now = datetime.utcnow()
    exp = now + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    payload: dict[str, Any] = {
        "sub": actor,  # Subject (actor)
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(exp.timestamp()),  # Expiration
    }

    # Optionally embed scopes in token (alternative: fetch from DB)
    if scopes:
        payload["scopes"] = scopes

    # TODO: Add unique JWT ID for revocation support
    # import uuid
    # payload["jti"] = str(uuid.uuid4())

    # Encode JWT
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,  # Convert to seconds
    )


# ============================================================================
# TOKEN ENDPOINT (TODO: Mount in router)
# ============================================================================


async def create_token_endpoint(actor: str, scopes: list[str] | None = None) -> TokenResponse:
    """
    Token creation endpoint handler.

    Args:
        actor: Actor identifier
        scopes: Optional scopes to grant

    Returns:
        TokenResponse: JWT token

    TODO: Add actor authentication (username/password, OAuth, etc.)
    TODO: Add scope validation (ensure actor is allowed requested scopes)
    TODO: Add rate limiting (prevent token abuse)

    Example Router:
        @router.post("/auth/token")
        async def token_endpoint(
            actor: str = Body(...),
            scopes: list[str] = Body([])
        ):
            return await create_token_endpoint(actor, scopes)
    """
    # TODO: Validate actor credentials before issuing token
    # For now, this is a stub that trusts the caller

    return generate_jwt_token(actor, scopes)


# ============================================================================
# TOKEN REVOCATION (TODO: Implement)
# ============================================================================


async def revoke_token(token: str) -> None:
    """
    Revoke a JWT token by adding to blacklist.

    Args:
        token: JWT token to revoke

    TODO: Implement Redis-backed token blacklist
    TODO: Add expiration to blacklist entries (match token exp)
    TODO: Add cleanup job for expired blacklist entries

    Redis Schema:
        Key: f"token_blacklist:{jti}"
        Value: "revoked"
        TTL: time_until_token_expires

    Example:
        await revoke_token(user_token)
        # Subsequent requests with this token will fail validation
    """
    # TODO: Extract jti from token
    # payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    # jti = payload.get("jti")

    # TODO: Add to Redis blacklist
    # redis = get_redis()
    # ttl = payload["exp"] - int(datetime.utcnow().timestamp())
    # await redis.setex(f"token_blacklist:{jti}", ttl, "revoked")

    raise NotImplementedError("Token revocation not yet implemented")


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if token is blacklisted.

    Args:
        jti: JWT ID (unique token identifier)

    Returns:
        bool: True if blacklisted, False otherwise

    TODO: Implement Redis check
    """
    # TODO: Check Redis
    # redis = get_redis()
    # result = await redis.get(f"token_blacklist:{jti}")
    # return result is not None

    return False


# ============================================================================
# SCOPE VALIDATION
# ============================================================================


def check_scopes(required_scopes: list[str], token_payload: dict[str, Any]) -> bool:
    """
    Check if token has required scopes.

    Args:
        required_scopes: List of required scopes
        token_payload: Decoded JWT payload

    Returns:
        bool: True if all required scopes are present

    TODO: Implement wildcard matching (e.g., "notion.*")
    TODO: Fetch scopes from database if not in token

    Example:
        if not check_scopes(["notion.write"], token_payload):
            raise HTTPException(403, "Insufficient permissions")
    """
    token_scopes = token_payload.get("scopes", [])

    # Check if all required scopes are present
    for required in required_scopes:
        if required not in token_scopes:
            # TODO: Implement wildcard matching
            # e.g., "notion.write" matches "notion.*"
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

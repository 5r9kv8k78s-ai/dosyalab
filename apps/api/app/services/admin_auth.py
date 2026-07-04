"""Admin Panel authentication/authorization.

Two independent checks, both enforced server-side (the web app's route
protection is UX only — this module is the actual security boundary):

1. The request's bearer token must be a Supabase Auth access token whose
   signature verifies against the Supabase project's own JWKS. A decoded-
   but-unverified JWT, or a client-supplied header like `X-Admin-Email`,
   is never trusted as authentication.
2. The token's verified `email` claim must appear in the backend-only
   `ADMIN_EMAILS` allowlist (see app.core.config.Settings.admin_email_set).
   A valid Supabase session alone does not make a user a DosyaLab admin.
"""

import logging
import threading
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AdminAuthError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class AdminIdentity:
    email: str


_jwks_client: PyJWKClient | None = None
_jwks_client_lock = threading.Lock()


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        with _jwks_client_lock:
            if _jwks_client is None:
                if not settings.supabase_url:
                    raise AdminAuthError(500, "Admin authentication is not configured.")
                jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
                _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        raise AdminAuthError(401, "Missing or invalid authentication.")
    token = header[len("bearer ") :].strip()
    if not token:
        raise AdminAuthError(401, "Missing or invalid authentication.")
    return token


def verify_supabase_access_token(token: str, settings: Settings) -> str:
    """Verifies `token`'s signature against the Supabase project's JWKS
    (asymmetric signing — RS256/ES256 — the current default for new
    Supabase projects) and returns its verified `email` claim.

    Never logs the token itself, never returns it in an error, and never
    accepts a payload without a cryptographically verified signature.
    """
    try:
        jwk_client = _get_jwks_client(settings)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            options={"verify_aud": bool(settings.supabase_jwt_audience)},
        )
    except AdminAuthError:
        raise
    except Exception as exc:
        # Any failure here (bad signature, expired, malformed, JWKS
        # unreachable) collapses to the same generic message — no detail
        # about *why* verification failed is returned to the client.
        raise AdminAuthError(401, "Invalid or expired authentication.") from exc

    email = payload.get("email")
    if not email:
        raise AdminAuthError(401, "Invalid or expired authentication.")
    return str(email)


def require_admin(
    request: Request, settings: Settings = Depends(get_settings)
) -> AdminIdentity:
    """FastAPI dependency for every `/api/v1/admin/*` route. Raises 401 for
    missing/invalid/unverifiable authentication, 403 for a valid Supabase
    session whose email isn't in `ADMIN_EMAILS`.
    """
    try:
        token = _extract_bearer_token(request)
        email = verify_supabase_access_token(token, settings)
    except AdminAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    normalized_email = email.strip().lower()
    if normalized_email not in settings.admin_email_set:
        logger.warning("admin_auth.forbidden")
        raise HTTPException(
            status_code=403, detail="This account is not authorized for the Admin Panel."
        )

    return AdminIdentity(email=normalized_email)

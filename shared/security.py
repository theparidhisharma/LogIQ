"""Password, JWT, tenant and API-key security primitives for LogIQ.

JWT implementation intentionally uses only Python's standard library so the
service has no hidden dependency on an unpinned crypto package. Use a strong,
unique LOGIQ_JWT_SECRET in every non-development deployment.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text


_bearer = HTTPBearer(auto_error=False)
JWT_SECRET = os.getenv("LOGIQ_JWT_SECRET", "development-only-change-this-secret")
JWT_ISSUER = os.getenv("LOGIQ_JWT_ISSUER", "logiq")
JWT_TTL_SECONDS = int(os.getenv("LOGIQ_JWT_TTL_SECONDS", "3600"))
_PASSWORD_ITERATIONS = 310_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    # Reject alternate encodings that differ only in unused base64 padding bits.
    if _b64(decoded) != value:
        raise ValueError("Non-canonical base64url encoding")
    return decoded


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(rounds))
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def issue_access_token(*, user_id: str, tenant_id: str, role: str, email: str) -> tuple[str, int]:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user_id, "tenant_id": tenant_id, "role": role, "email": email,
               "iss": JWT_ISSUER, "iat": now, "exp": now + JWT_TTL_SECONDS}
    body = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}", JWT_TTL_SECONDS


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_unb64(header_part))
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported JWT header")
        body = f"{header_part}.{payload_part}"
        expected = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature_part)):
            raise ValueError("Invalid signature")
        claims = json.loads(_unb64(payload_part))
        now = int(time.time())
        if claims.get("iss") != JWT_ISSUER or not claims.get("sub") or int(claims.get("exp", 0)) <= now:
            raise ValueError("Expired or invalid claims")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer access token required", headers={"WWW-Authenticate": "Bearer"})
    claims = decode_access_token(credentials.credentials)
    from shared.common import identity_db
    with identity_db().connect() as conn:
        row = conn.execute(text("""SELECT id,email,tenant_id,role,is_active FROM users WHERE id=:id"""),
                           {"id": claims["sub"]}).mappings().first()
    if not row or not row["is_active"] or row["tenant_id"] != claims.get("tenant_id"):
        raise HTTPException(401, "User session is no longer valid")
    return dict(row)


def require_roles(*roles: str):
    def dependency(user: dict[str, Any] = Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Insufficient role for this operation")
        return user
    return dependency


def create_api_key_material() -> tuple[str, str]:
    raw = "lgq_" + secrets.token_urlsafe(32)
    pepper = os.getenv("LOGIQ_API_KEY_PEPPER", "")
    digest = hashlib.sha256((pepper + raw).encode()).hexdigest()
    return raw, digest


def authenticate_api_key(request: Request) -> dict[str, Any]:
    supplied = request.headers.get("x-api-key")
    if not supplied:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
    if not supplied:
        raise HTTPException(401, "API key required")
    pepper = os.getenv("LOGIQ_API_KEY_PEPPER", "")
    digest = hashlib.sha256((pepper + supplied).encode()).hexdigest()
    from shared.common import identity_db
    with identity_db().connect() as conn:
        row = conn.execute(text("""SELECT id,tenant_id,application_id,scopes FROM api_keys
            WHERE key_hash=:digest AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > now())"""), {"digest": digest}).mappings().first()
    if not row:
        raise HTTPException(401, "Invalid or revoked API key")
    context = dict(row)
    if 'ingest' not in (context.get('scopes') or []):
        raise HTTPException(403, 'API key does not have ingestion permission')
    request.state.tenant_id = context["tenant_id"]
    request.state.application_id = context.get("application_id")
    return context

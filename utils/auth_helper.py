import os
import functools
from flask import request, jsonify, g
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from memory.report_db import report_db

# Secret key configuration for cryptographic token signatures
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY") or os.getenv("SECRET_KEY") or "enterprise-decision-engine-jwt-secret-2025"
TOKEN_MAX_AGE_SECONDS = int(os.getenv("TOKEN_EXPIRATION_SECONDS", str(86400 * 30)))  # Default: 30 days

_serializer = URLSafeTimedSerializer(AUTH_SECRET_KEY, salt="enterprise-auth-token")


def generate_auth_token(user_id: str, email: str) -> str:
    """Generates a cryptographically signed, URL-safe, time-stamped authentication token."""
    payload = {
        "user_id": str(user_id),
        "email": str(email).lower()
    }
    return _serializer.dumps(payload)


def verify_auth_token(token: str) -> dict | None:
    """
    Decodes and cryptographically verifies an authentication token.
    Returns the payload dictionary {"user_id": ..., "email": ...} if valid, else None.
    """
    if not token or not isinstance(token, str):
        return None

    # Handle 'Bearer <token>' prefix if passed directly
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    try:
        data = _serializer.loads(clean_token, max_age=TOKEN_MAX_AGE_SECONDS)
        return data
    except (SignatureExpired, BadSignature, Exception):
        return None


def get_authenticated_user() -> dict | None:
    """
    Extracts and validates the authenticated user from the Authorization header.
    Returns user dict from database if authenticated, else None.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        # Fallback check for auth token in query param or body for export links
        auth_header = request.args.get("token", "")

    if not auth_header:
        return None

    payload = verify_auth_token(auth_header)
    if not payload or not payload.get("user_id"):
        return None

    user = report_db.get_user_by_id(payload["user_id"])
    return user


def require_auth(f):
    """
    Flask route decorator to enforce authentication on protected endpoints.
    Attaches authenticated user record to Flask's `g.user` and `request.user`.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in to continue."
            }), 401

        # Attach authenticated user to request context
        g.user = user
        request.user = user
        request.user_id = user["id"]
        return f(*args, **kwargs)

    return decorated_function


def optional_auth(f):
    """
    Flask route decorator for endpoints that can be accessed with or without authentication.
    If valid token is present, attaches user to `g.user` and `request.user`.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        g.user = user
        request.user = user
        request.user_id = user["id"] if user else None
        return f(*args, **kwargs)

    return decorated_function

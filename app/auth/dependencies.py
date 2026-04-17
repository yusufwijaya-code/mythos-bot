from fastapi import Request, HTTPException, status
from app.auth.jwt_handler import verify_token


def get_current_user(request: Request) -> dict:
    """FastAPI dependency to extract and verify user from JWT token.

    Checks:
    1. Authorization header (Bearer token)
    2. Cookie (access_token)
    """
    token = None

    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Check cookie fallback
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {"email": payload["sub"]}

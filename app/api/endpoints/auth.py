from fastapi import APIRouter, Request, HTTPException, Response
from pydantic import BaseModel
from loguru import logger

from config.settings import settings
from app.auth.jwt_handler import create_access_token, is_authorized_email
from app.auth.oauth import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    """Authenticate user with email and password."""
    email = req.email.strip().lower()

    # Check if email is authorized
    if not is_authorized_email(email):
        logger.warning(f"Login attempt from unauthorized email: {email}")
        raise HTTPException(
            status_code=403,
            detail="Email is not authorized to access this system"
        )

    # Verify password
    if not verify_password(req.password, settings.AUTH_PASSWORD_HASH):
        logger.warning(f"Failed login attempt for: {email}")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Create JWT token
    access_token = create_access_token(email)

    logger.info(f"User logged in: {email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": email,
        },
    }


@router.get("/me")
def get_me(request: Request):
    """Get current user info from token."""
    from app.auth.dependencies import get_current_user
    try:
        user = get_current_user(request)
        return {"authenticated": True, "user": user}
    except HTTPException:
        return {"authenticated": False, "user": None}


@router.post("/logout")
def logout(response: Response):
    """Clear auth cookie."""
    response.delete_cookie("access_token")
    return {"status": "ok", "message": "Logged out"}

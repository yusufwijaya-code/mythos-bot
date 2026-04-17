from datetime import datetime, timedelta, timezone
import jwt
from loguru import logger

from config.settings import settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def create_access_token(email: str) -> str:
    """Create a JWT token for authenticated user."""
    payload = {
        "sub": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify JWT token and return payload. Returns None if invalid."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def is_authorized_email(email: str) -> bool:
    """Check if email is in the authorized list."""
    return email.lower() in [e.lower() for e in settings.AUTHORIZED_EMAILS]

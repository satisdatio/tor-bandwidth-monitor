"""Authentication and authorization."""

from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt

from ..config import Config


security = HTTPBearer()


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[EmailStr] = None
    roles: List[str] = ["viewer"]
    is_active: bool = True
    created_at: datetime = datetime.utcnow()


class UserInDB(User):
    """User with hashed password."""
    hashed_password: str


class Token(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload."""
    username: Optional[str] = None
    roles: List[str] = []


# In-memory user store (replace with database in production)
_users_db: dict = {}


def init_auth(config: Config):
    """Initialize authentication with default admin user."""
    # Create default admin if no users exist
    if not _users_db:
        admin_password = "admin"  # Should be changed on first login
        hashed = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        _users_db["admin"] = UserInDB(
            username="admin",
            email="admin@localhost",
            roles=["admin", "operator", "viewer"],
            hashed_password=hashed.decode()
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Hash password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    return _users_db.get(username)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_access_token(config: Config, data: dict) -> tuple[str, int]:
    """Create JWT access token."""
    to_encode = data.copy()
    expires_delta = timedelta(minutes=config.security.token_expiry_minutes)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    
    encoded = jwt.encode(
        to_encode,
        config.security.secret_key,
        algorithm="HS256"
    )
    return encoded, config.security.token_expiry_minutes * 60


async def get_current_user(
    config: Config = Depends(lambda: None),  # Injected via app state
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            config.security.secret_key,
            algorithms=["HS256"]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        roles = payload.get("roles", [])
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(*roles: str):
    """Decorator to require specific roles."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not any(role in current_user.roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Role definitions
ROLE_VIEWER = "viewer"      # Read-only access
ROLE_OPERATOR = "operator"  # Can acknowledge alerts, modify config
ROLE_ADMIN = "admin"        # Full access including user management
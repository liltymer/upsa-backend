import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student

# Load environment variables
load_dotenv()

# ===============================
# SECURITY CONFIG
# ===============================

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env")

# 11 rounds: above the recommended minimum of 10, and about half the time of 12
# on a small server. Hashes made with other costs are replaced at the next sign-in.
BCRYPT_ROUNDS = 11
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=BCRYPT_ROUNDS,
    bcrypt__min_rounds=BCRYPT_ROUNDS,
    bcrypt__max_rounds=BCRYPT_ROUNDS,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_DUMMY_HASH = pwd_context.hash("timing-equaliser")


# ===============================
# PASSWORD FUNCTIONS
# ===============================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    Capped at 72 bytes: bcrypt hard limit.
    """
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """
    Verify a plain password against its bcrypt hash.
    With no hash (unknown user) a dummy hash is still checked so the
    response time does not reveal whether an account exists.
    """
    if hashed_password is None:
        pwd_context.verify(plain_password[:72], _DUMMY_HASH)
        return False
    return pwd_context.verify(plain_password[:72], hashed_password)


def verify_and_update(plain_password: str, hashed_password: str | None) -> tuple[bool, str | None]:
    """Like verify_password, and also returns a new hash when the stored one uses another cost."""
    if hashed_password is None:
        pwd_context.verify(plain_password[:72], _DUMMY_HASH)
        return False, None
    return pwd_context.verify_and_update(plain_password[:72], hashed_password)


# ===============================
# JWT TOKEN FUNCTIONS
# ===============================

def create_access_token(data: dict) -> str:
    """
    Create a signed JWT access token with expiry.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "sub": str(data.get("sub"))
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ===============================
# CURRENT USER DEPENDENCY
# ===============================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Student:
    """
    Decode JWT and return the authenticated student.
    Raises 401 if token is missing, invalid, or expired.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")

        if user_id is None or payload.get("type", "access") != "access":
            raise credentials_exception
        user_id = int(user_id)

    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(Student).filter(Student.id == user_id).first()

    if user is None:
        raise credentials_exception

    return user


# ===============================
# ADMIN GUARD
# ===============================

def require_admin(current_user: Student = Depends(get_current_user)) -> Student:
    """
    Allows the request through only for admin accounts.
    Raises 403 for everyone else.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user

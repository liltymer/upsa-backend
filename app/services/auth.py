import os
from datetime import datetime, timedelta
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

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ===============================
# PASSWORD FUNCTIONS
# ===============================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    Capped at 72 bytes — bcrypt hard limit.
    """
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its bcrypt hash.
    """
    return pwd_context.verify(plain_password[:72], hashed_password)


# ===============================
# JWT TOKEN FUNCTIONS
# ===============================

def create_access_token(data: dict) -> str:
    """
    Create a signed JWT access token with expiry.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
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

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(Student).filter(Student.id == int(user_id)).first()

    if user is None:
        raise credentials_exception

    return user
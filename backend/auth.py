"""
Authentication module for HealthLink AI
Handles password hashing and JWT token management
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session

try:
    from .db_manager import SessionLocal, User
except ImportError:
    from db_manager import SessionLocal, User

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "healthlink-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
PASSWORD_SALT = "healthlink-salt-2024"  # In production, use per-user salt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Hash the plain password and compare
    expected_hash = hashlib.sha256((plain_password + PASSWORD_SALT).encode()).hexdigest()
    return expected_hash == hashed_password


def get_password_hash(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256((password + PASSWORD_SALT).encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID"""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def create_user(username: str, password: str, email: Optional[str] = None, 
                is_admin: bool = False, role: str = "patient", specialty: str = None) -> Optional[User]:
    """Create a new user with role (patient/doctor/admin)"""
    db = SessionLocal()
    try:
        # Check if username already exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"Username {username} already exists")
            return None
        
        new_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_admin=1 if is_admin or role == "admin" else 0,
            role=role,
            specialty=specialty
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"User {username} created successfully as {role}")
        return new_user
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

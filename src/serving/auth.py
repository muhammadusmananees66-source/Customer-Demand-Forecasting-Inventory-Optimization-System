"""
Authentication module for API
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt
import structlog
from fastapi import HTTPException

logger = structlog.get_logger()

# Get JWT secret from environment
JWT_SECRET: str = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES: int = int(os.environ.get("JWT_EXPIRY_MINUTES", 60))


class AuthManager:
    """Authentication manager for JWT tokens"""

    def __init__(self) -> None:
        self._users: dict[str, str] = self._load_users()

    # def _load_users(self) -> Dict[str, str]:
    #     """Load users from environment or use default"""
    #     users_json: str = os.environ.get("USERS", "{}")
    #     try:
    #         raw_users: Dict[str, str] = json.loads(users_json)
    #         return {
    #             username: bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    #             for username, password in raw_users.items()
    #         }
    #     except json.JSONDecodeError:
    #         # Default test user (for development only)
    #         if os.environ.get("ENVIRONMENT", "development") == "development":
    #             return {
    #                 "admin": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
    #                 "user": bcrypt.hashpw("user123".encode(), bcrypt.gensalt()).decode()
    #             }
    #         return {}
    def _load_users(self) -> dict[str, str]:
        """Load users from environment or use default"""
        users_json: str = os.environ.get("USERS", "{}")
        try:
            raw_users: dict[str, str] = json.loads(users_json)
        except json.JSONDecodeError:
            raw_users = {}

        if not raw_users and os.environ.get("ENVIRONMENT", "development") == "development":
            # No USERS configured -- seed dev defaults so local/CI auth
            # actually works. The old code only reached this branch on a
            # JSONDecodeError, but the default value "{}" is valid JSON
            # (an empty dict), so this fallback was unreachable in the
            # normal case of USERS simply not being set.
            raw_users = {"admin": "admin123", "user": "user123"}

        return {
            username: bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            for username, password in raw_users.items()
        }

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """Authenticate user"""
        if username not in self._users:
            return None

        stored_hash: str = self._users[username]
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            return {
                "user_id": username,
                "roles": ["admin", "user"] if username == "admin" else ["user"],
                "username": username,
            }
        return None

    def create_token(self, user_data: dict[str, Any]) -> str:
        """Create JWT token"""
        payload: dict[str, Any] = {
            "user_id": user_data["user_id"],
            "roles": user_data.get("roles", ["user"]),
            "username": user_data["username"],
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES),
            "iat": datetime.utcnow(),
        }
        token: str = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token"""
        try:
            payload: dict[str, Any] = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(status_code=401, detail="Token expired") from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail="Invalid token") from e


# Singleton instance
auth_manager: AuthManager = AuthManager()

# tests/unit/test_auth.py - NEW FILE
"""
Unit tests for Authentication module
"""

from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from src.serving.auth import AuthManager


class TestAuthManager:
    """Test AuthManager class"""

    def test_auth_manager_creation(self):
        """Test AuthManager initialization"""
        auth = AuthManager()
        assert auth._users is not None
        assert "admin" in auth._users
        assert "user" in auth._users

    def test_authenticate_success(self):
        """Test successful authentication"""
        auth = AuthManager()
        result = auth.authenticate("admin", "admin123")
        assert result is not None
        assert result["user_id"] == "admin"
        assert "admin" in result["roles"]

    def test_authenticate_failure(self):
        """Test failed authentication"""
        auth = AuthManager()
        result = auth.authenticate("invalid", "invalid")
        assert result is None

    def test_create_token(self):
        """Test token creation"""
        auth = AuthManager()
        user_data = {"user_id": "test", "username": "test", "roles": ["user"]}
        token = auth.create_token(user_data)
        assert token is not None
        assert isinstance(token, str)

    def test_verify_token_success(self):
        """Test successful token verification"""
        auth = AuthManager()
        user_data = {"user_id": "test", "username": "test", "roles": ["user"]}
        token = auth.create_token(user_data)
        payload = auth.verify_token(token)
        assert payload["user_id"] == "test"
        assert payload["username"] == "test"

    def test_verify_token_expired(self):
        """Test expired token verification"""
        with patch("src.serving.auth.JWT_EXPIRY_MINUTES", 0.1):
            auth = AuthManager()
            user_data = {"user_id": "test", "username": "test", "roles": ["user"]}
            token = auth.create_token(user_data)

            # Mock expiration
            with patch("jwt.decode") as mock_decode:
                mock_decode.side_effect = jwt.ExpiredSignatureError
                with pytest.raises(HTTPException) as exc:
                    auth.verify_token(token)
                assert exc.value.status_code == 401
                assert "expired" in exc.value.detail.lower()

    def test_verify_token_invalid(self):
        """Test invalid token verification"""
        auth = AuthManager()
        with patch("jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError
            with pytest.raises(HTTPException) as exc:
                auth.verify_token("invalid_token")
            assert exc.value.status_code == 401
            assert "invalid" in exc.value.detail.lower()

# tests/unit/test_dependencies.py - NEW FILE
"""
Unit tests for Dependencies module
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.serving.dependencies import get_current_user, security


class TestDependencies:
    """Test dependencies"""

    def test_security_exists(self):
        """Test security singleton exists"""
        assert security is not None

    @patch("src.serving.dependencies.auth_manager")
    async def test_get_current_user_success(self, mock_auth):
        """Test successful user retrieval"""
        mock_auth.verify_token.return_value = {"user_id": "test", "username": "test"}
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")
        result = await get_current_user(credentials)
        assert result["user_id"] == "test"

    @patch("src.serving.dependencies.auth_manager")
    async def test_get_current_user_invalid(self, mock_auth):
        """Test invalid user retrieval"""
        mock_auth.verify_token.side_effect = HTTPException(status_code=401, detail="Invalid token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials)
        assert exc.value.status_code == 401

    @patch("src.serving.dependencies.auth_manager")
    async def test_get_current_user_error(self, mock_auth):
        """Test error during user retrieval"""
        mock_auth.verify_token.side_effect = Exception("Unexpected error")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials)
        assert exc.value.status_code == 401

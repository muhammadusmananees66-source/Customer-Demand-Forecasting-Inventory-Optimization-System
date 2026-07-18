# """
# Dependency injection for API
# """

# from typing import Dict, Any
# from fastapi import Request, HTTPException, Depends
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from src.serving.auth import auth_manager

# security = HTTPBearer()


# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security)  # noqa: B008
# ) -> Dict[str, Any]:
#     """Get current user from JWT token"""
#     try:
#         payload = auth_manager.verify_token(credentials.credentials)
#         return payload
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


"""
Dependency injection for API
"""

from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.serving.auth import auth_manager

# ✅ Create module-level singleton
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008,
) -> dict[str, Any]:
    """Get current user from JWT token"""
    try:
        payload = auth_manager.verify_token(credentials.credentials)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}") from e

"""
Athena Server v2 - Authentication Utilities

Shared authentication dependencies for API routes.
"""

from fastapi import Header, HTTPException

from config import settings


async def verify_api_key(authorization: str = Header(None)):
    """
    Verify API key for protected endpoints.

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        True if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    if not settings.ATHENA_API_KEY:
        return True  # No auth in development

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "")
    if token != settings.ATHENA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True

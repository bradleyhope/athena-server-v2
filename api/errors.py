"""
Athena Server v2 - Error Handling Utilities

Standardized error handling for API routes.
"""

import logging
from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException

logger = logging.getLogger("athena.api.errors")


class NotFoundError(Exception):
    """Resource not found."""
    pass


class ValidationError(Exception):
    """Validation failed."""
    pass


class OperationError(Exception):
    """Operation failed."""
    pass


def handle_api_errors(operation_name: str):
    """
    Decorator for standardized API error handling.

    Catches exceptions and converts them to appropriate HTTP responses:
    - HTTPException: re-raised as-is
    - NotFoundError: 404 response
    - ValidationError: 400 response
    - OperationError: 400 response
    - Other exceptions: 500 response with logging

    Usage:
        @router.get("/items/{item_id}")
        @handle_api_errors("get item")
        async def get_item(item_id: str):
            item = get_item_from_db(item_id)
            if not item:
                raise NotFoundError("Item not found")
            return item

    Args:
        operation_name: Human-readable name for the operation (used in error logs)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise FastAPI HTTP exceptions as-is
                raise
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except OperationError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to {operation_name}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        return wrapper
    return decorator


def not_found(message: str = "Resource not found"):
    """Raise a 404 Not Found error."""
    raise HTTPException(status_code=404, detail=message)


def bad_request(message: str = "Bad request"):
    """Raise a 400 Bad Request error."""
    raise HTTPException(status_code=400, detail=message)


def server_error(message: str = "Internal server error"):
    """Raise a 500 Internal Server error."""
    raise HTTPException(status_code=500, detail=message)

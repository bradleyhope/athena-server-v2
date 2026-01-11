"""
Athena Server v2 - Boundary Enforcement Middleware

This middleware intercepts all API requests and checks them against the
boundaries defined in the brain's boundaries table. This ensures that
all actions, regardless of origin, are subject to the same rules.

Boundary Types:
- hard: Absolute restrictions that cannot be bypassed
- soft: Guidelines that can be overridden with approval
- contextual: Rules that apply in specific contexts
"""

import logging
import json
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from db.brain import get_boundaries

logger = logging.getLogger("athena.middleware.boundary")


# Define action categories based on API paths and methods
ACTION_CATEGORY_MAP = {
    # Email-related actions
    (r"/api/.*email.*", "POST"): "email",
    (r"/api/.*send.*", "POST"): "communication",
    
    # Financial actions
    (r"/api/.*payment.*", "POST"): "financial",
    (r"/api/.*purchase.*", "POST"): "financial",
    (r"/api/.*stripe.*", "POST"): "financial",
    
    # Brain modification actions
    (r"/api/brain/identity.*", "PUT"): "identity_modification",
    (r"/api/brain/identity.*", "POST"): "identity_modification",
    (r"/api/brain/boundaries.*", "PUT"): "boundary_modification",
    (r"/api/brain/boundaries.*", "POST"): "boundary_modification",
    (r"/api/brain/boundaries.*", "DELETE"): "boundary_modification",
    
    # Evolution actions
    (r"/api/evolution.*", "POST"): "evolution",
    (r"/api/evolution/.*/apply", "POST"): "evolution_apply",
    
    # Workflow execution
    (r"/api/workflows/.*/execute", "POST"): "workflow_execution",
    
    # External API calls
    (r"/api/manus.*", "POST"): "external_api",
    (r"/api/notion.*", "POST"): "external_api",
    
    # Data deletion
    (r"/api/.*", "DELETE"): "data_deletion",
}


class BoundaryCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces boundaries on all API requests.
    
    For each request, it:
    1. Determines the action category based on path and method
    2. Fetches relevant boundaries from the database
    3. Checks if any hard boundaries are violated
    4. Adds warnings for soft boundary concerns
    5. Logs all boundary checks for audit purposes
    """
    
    def __init__(self, app: ASGIApp, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/api/health",
            "/api/status",
            "/docs",
            "/openapi.json",
            "/",
        ]
        self._boundary_cache = None
        self._cache_timestamp = None
        self._cache_ttl_seconds = 60  # Refresh boundaries every minute
    
    async def dispatch(self, request: Request, call_next):
        """Process each request through boundary checks."""
        
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)
        
        # Skip GET requests (read-only operations)
        if request.method == "GET":
            return await call_next(request)
        
        # Determine the action category
        category = self._get_action_category(path, request.method)
        
        if not category:
            # No specific category, allow the request
            return await call_next(request)
        
        # Get boundaries for this category
        boundaries = self._get_cached_boundaries()
        relevant_boundaries = [
            b for b in boundaries 
            if b.get('category') == category or b.get('category') == 'all'
        ]
        
        if not relevant_boundaries:
            # No boundaries for this category
            return await call_next(request)
        
        # Check boundaries
        violation = self._check_boundaries(relevant_boundaries, request, category)
        
        if violation:
            boundary_type, boundary = violation
            
            if boundary_type == "hard":
                # Log the violation
                logger.warning(
                    f"HARD BOUNDARY VIOLATION: {category} | "
                    f"Path: {path} | Rule: {boundary.get('rule')}"
                )
                
                # Return 403 Forbidden
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "boundary_violation",
                        "type": "hard",
                        "category": category,
                        "rule": boundary.get('rule'),
                        "message": f"This action is not allowed: {boundary.get('description', boundary.get('rule'))}",
                        "boundary_id": str(boundary.get('id')),
                    }
                )
            
            elif boundary_type == "soft":
                # Log the soft boundary trigger
                logger.info(
                    f"SOFT BOUNDARY TRIGGERED: {category} | "
                    f"Path: {path} | Rule: {boundary.get('rule')}"
                )
                
                # Check if approval is required
                if boundary.get('requires_approval'):
                    # Add a header indicating approval is needed
                    response = await call_next(request)
                    response.headers["X-Athena-Boundary-Warning"] = boundary.get('rule', 'Approval required')
                    response.headers["X-Athena-Requires-Approval"] = "true"
                    return response
        
        # No violations, proceed with the request
        response = await call_next(request)
        
        # Add audit header
        response.headers["X-Athena-Boundary-Check"] = "passed"
        
        return response
    
    def _get_action_category(self, path: str, method: str) -> Optional[str]:
        """
        Determine the action category based on the request path and method.
        
        Returns:
            Category string or None if no category matches
        """
        for (pattern, req_method), category in ACTION_CATEGORY_MAP.items():
            if method == req_method and re.match(pattern, path, re.IGNORECASE):
                return category
        return None
    
    def _get_cached_boundaries(self) -> list:
        """
        Get boundaries from cache or refresh from database.
        
        Returns:
            List of boundary dictionaries
        """
        now = datetime.now()
        
        if (self._boundary_cache is None or 
            self._cache_timestamp is None or
            (now - self._cache_timestamp).total_seconds() > self._cache_ttl_seconds):
            
            try:
                self._boundary_cache = get_boundaries(active_only=True)
                self._cache_timestamp = now
                logger.debug(f"Refreshed boundary cache: {len(self._boundary_cache)} boundaries")
            except Exception as e:
                logger.error(f"Failed to fetch boundaries: {e}")
                if self._boundary_cache is None:
                    self._boundary_cache = []
        
        return self._boundary_cache
    
    def _check_boundaries(
        self, 
        boundaries: list, 
        request: Request, 
        category: str
    ) -> Optional[Tuple[str, Dict]]:
        """
        Check if any boundaries are violated.
        
        Args:
            boundaries: List of relevant boundaries
            request: The incoming request
            category: The action category
            
        Returns:
            Tuple of (boundary_type, boundary_dict) if violated, None otherwise
        """
        # Sort boundaries: hard first, then soft, then contextual
        type_order = {"hard": 0, "soft": 1, "contextual": 2}
        sorted_boundaries = sorted(
            boundaries, 
            key=lambda b: type_order.get(b.get('boundary_type', 'contextual'), 3)
        )
        
        for boundary in sorted_boundaries:
            boundary_type = boundary.get('boundary_type', 'soft')
            
            # Check if this boundary applies
            if self._boundary_applies(boundary, request, category):
                # Check for exceptions
                exceptions = boundary.get('exceptions', [])
                if isinstance(exceptions, str):
                    try:
                        exceptions = json.loads(exceptions)
                    except:
                        exceptions = []
                
                # Check if any exception applies
                exception_applies = False
                for exception in exceptions:
                    if self._exception_applies(exception, request):
                        exception_applies = True
                        break
                
                if not exception_applies:
                    return (boundary_type, boundary)
        
        return None
    
    def _boundary_applies(self, boundary: Dict, request: Request, category: str) -> bool:
        """
        Check if a specific boundary applies to this request.
        
        For now, we apply all boundaries in the matching category.
        This can be extended to check specific conditions in the boundary rule.
        """
        # All boundaries in the category apply by default
        return True
    
    def _exception_applies(self, exception: Dict, request: Request) -> bool:
        """
        Check if an exception to a boundary applies.
        
        Exceptions can be based on:
        - User/role (if authentication is implemented)
        - Time of day
        - Specific conditions
        """
        # TODO: Implement exception logic based on exception type
        # For now, no exceptions apply
        return False


def get_boundary_check_middleware(excluded_paths: list = None):
    """
    Factory function to create the boundary check middleware.
    
    Args:
        excluded_paths: List of path prefixes to exclude from boundary checks
        
    Returns:
        Configured BoundaryCheckMiddleware class
    """
    return lambda app: BoundaryCheckMiddleware(app, excluded_paths=excluded_paths)

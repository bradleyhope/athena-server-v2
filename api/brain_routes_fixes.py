# This file contains the additional endpoints to be added to brain_routes.py
# These are the fixes for the comprehensive test failures

"""
FIXES NEEDED:
1. Add GET /api/brain/preferences endpoint
2. Add GET /api/brain/pending-actions endpoint (alias for /api/brain/actions/pending)
3. Add GET /api/brain/evolution endpoint (alias for /api/brain/evolution/proposals)
4. Make /api/health public (in main.py)
5. Add trigger endpoints for observation_burst and pattern_detection
"""

# Add these imports to db/brain.py:
# def get_preferences(category: str = None) -> list

# Add these routes to brain_routes.py:

"""
# =============================================================================
# PREFERENCES ENDPOINT (KNOWLEDGE LAYER)
# =============================================================================

@router.get("/preferences")
async def list_preferences(category: Optional[str] = None):
    \"\"\"Get all preferences, optionally filtered by category.\"\"\"
    try:
        preferences = get_preferences(category)
        return {"count": len(preferences), "preferences": preferences}
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ALIAS ENDPOINTS FOR CONVENIENCE
# =============================================================================

@router.get("/pending-actions")
async def list_pending_actions_alias(
    status: str = "pending",
    priority: Optional[str] = None
):
    \"\"\"Alias for /actions/pending - Get pending actions.\"\"\"
    try:
        actions = get_pending_actions(status, priority)
        return {"count": len(actions), "actions": actions}
    except Exception as e:
        logger.error(f"Failed to get pending actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution")
async def list_evolution_proposals_alias(status: str = "proposed"):
    \"\"\"Alias for /evolution/proposals - Get evolution proposals.\"\"\"
    try:
        proposals = get_evolution_proposals(status)
        return {"count": len(proposals), "proposals": proposals}
    except Exception as e:
        logger.error(f"Failed to get evolution proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""

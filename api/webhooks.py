"""
GitHub Webhook Handler for Bidirectional Sync

Handles GitHub push events to sync context file changes back to database.
Part of Phase 7: Bidirectional Sync.
"""

import os
import hmac
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from datetime import datetime

logger = logging.getLogger("athena.webhooks")
router = APIRouter()

# Get webhook secret from environment
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Handle GitHub webhook for context file changes.
    
    Triggered on push events to cogos-system repository.
    Syncs changed context files back to Neon database.
    
    Security:
    - HMAC SHA-256 signature verification
    - Only processes master branch pushes
    - Only syncs context files (not workflows)
    
    Returns:
        Dict with sync status and results
    """
    logger.info("Received GitHub webhook")
    
    # Get raw payload for signature verification
    payload = await request.body()
    
    # Verify signature
    if not verify_signature(payload, x_hub_signature_256):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse JSON payload
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Check if push event to master branch
    ref = data.get("ref", "")
    if ref != "refs/heads/master":
        logger.info(f"Ignoring push to {ref} (not master)")
        return {
            "status": "ignored",
            "reason": "not master branch",
            "ref": ref
        }
    
    # Get repository info
    repository = data.get("repository", {})
    repo_name = repository.get("full_name", "unknown")
    
    if repo_name != "bradleyhope/cogos-system":
        logger.info(f"Ignoring push to {repo_name} (not cogos-system)")
        return {
            "status": "ignored",
            "reason": "not cogos-system repository",
            "repository": repo_name
        }
    
    # Get commits and changed files
    commits = data.get("commits", [])
    changed_files = set()
    
    for commit in commits:
        # Add modified files
        for file in commit.get("modified", []):
            changed_files.add(file)
        # Add added files
        for file in commit.get("added", []):
            changed_files.add(file)
    
    # Filter for context files only (exclude workflows)
    context_files = [
        f for f in changed_files
        if f.startswith("docs/athena/context/") 
        and not f.startswith("docs/athena/context/workflows/")
        and not f.startswith("docs/athena/context/documentation/")
        and f.endswith(".md")
    ]
    
    if not context_files:
        logger.info(f"No context files changed in {len(commits)} commits")
        return {
            "status": "ignored",
            "reason": "no context files changed",
            "total_files": len(changed_files),
            "context_files": 0
        }
    
    logger.info(f"Found {len(context_files)} context files to sync: {context_files}")
    
    # Get commit info
    head_commit = data.get("head_commit", {})
    commit_sha = head_commit.get("id", "unknown")
    commit_message = head_commit.get("message", "")
    commit_author = head_commit.get("author", {}).get("name", "unknown")
    commit_timestamp = head_commit.get("timestamp", datetime.utcnow().isoformat())
    
    # Trigger sync in background
    background_tasks.add_task(
        sync_from_github_task,
        context_files,
        commit_sha,
        commit_message,
        commit_author,
        commit_timestamp
    )
    
    return {
        "status": "accepted",
        "context_files": context_files,
        "commit_sha": commit_sha[:7],
        "commit_message": commit_message,
        "commit_author": commit_author,
        "message": "Sync triggered in background"
    }


def verify_signature(payload: bytes, signature: Optional[str]) -> bool:
    """
    Verify GitHub webhook signature using HMAC SHA-256.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        logger.warning("No signature provided")
        return False
    
    if not WEBHOOK_SECRET:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        return False
    
    # Compute expected signature
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected, signature)
    
    if not is_valid:
        logger.warning(f"Signature mismatch: expected {expected[:20]}..., got {signature[:20]}...")
    
    return is_valid


async def sync_from_github_task(
    context_files: list[str],
    commit_sha: str,
    commit_message: str,
    commit_author: str,
    commit_timestamp: str
):
    """
    Background task to sync context files from GitHub to database.
    
    Args:
        context_files: List of changed context file paths
        commit_sha: Git commit SHA
        commit_message: Commit message
        commit_author: Commit author name
        commit_timestamp: Commit timestamp (ISO format)
    """
    logger.info(f"Starting sync task for {len(context_files)} files")
    logger.info(f"Commit: {commit_sha[:7]} by {commit_author}")
    logger.info(f"Message: {commit_message}")
    
    try:
        # Import sync script
        from scripts.sync_from_github import sync_from_github
        
        # Run sync
        result = await sync_from_github(
            context_files,
            commit_sha,
            commit_message,
            commit_author,
            commit_timestamp
        )
        
        # Log results
        synced = result.get("synced", [])
        skipped = result.get("skipped", [])
        errors = result.get("errors", [])
        
        logger.info(f"Sync complete: {len(synced)} synced, {len(skipped)} skipped, {len(errors)} errors")
        
        if synced:
            logger.info(f"Synced files: {synced}")
        if skipped:
            logger.info(f"Skipped files: {skipped}")
        if errors:
            logger.error(f"Errors: {errors}")
        
    except Exception as e:
        logger.error(f"Sync task failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


@router.get("/webhooks/github/status")
async def webhook_status():
    """
    Get webhook configuration status.
    
    Returns:
        Dict with webhook configuration info
    """
    return {
        "webhook_configured": bool(WEBHOOK_SECRET),
        "endpoint": "/webhooks/github",
        "supported_events": ["push"],
        "supported_branches": ["master"],
        "supported_files": [
            "docs/athena/context/canonical-memory.md",
            "docs/athena/context/policies.md"
        ],
        "note": "Other context files are read-only from GitHub"
    }

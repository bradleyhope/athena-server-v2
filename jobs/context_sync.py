"""
Context Sync Job

Scheduled job that syncs context from Neon database to GitHub repository.
Runs daily to keep GitHub context files up-to-date with database changes.

This job:
1. Fetches boundaries from Neon → updates policies.md
2. Fetches canonical_memory from Neon → updates canonical-memory.md
3. Commits and pushes changes to GitHub if any updates occurred

Scheduled to run: Daily at 2:00 AM London time
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sync_context_to_github import (
    sync_policies,
    sync_canonical_memory,
    commit_and_push_changes
)

logger = logging.getLogger("athena.jobs.context_sync")


async def run_context_sync(dry_run: bool = False):
    """
    Run the context sync job.
    
    Args:
        dry_run: If True, sync files but don't commit/push to GitHub
        
    Returns:
        Dict with status and details
    """
    logger.info("Starting context sync job")
    start_time = datetime.now()
    
    result = {
        "status": "success",
        "synced_files": [],
        "errors": [],
        "duration_seconds": 0,
        "dry_run": dry_run
    }
    
    try:
        # Sync policies
        logger.info("Syncing policies...")
        if sync_policies():
            result["synced_files"].append("policies.md")
            logger.info("✅ Policies synced")
        else:
            result["errors"].append("Failed to sync policies")
            logger.error("❌ Policies sync failed")
        
        # Sync canonical memory
        logger.info("Syncing canonical memory...")
        if sync_canonical_memory():
            result["synced_files"].append("canonical-memory.md")
            logger.info("✅ Canonical memory synced")
        else:
            result["errors"].append("Failed to sync canonical memory")
            logger.error("❌ Canonical memory sync failed")
        
        # Commit and push if not dry run
        if not dry_run and not result["errors"]:
            logger.info("Committing and pushing changes to GitHub...")
            if commit_and_push_changes():
                logger.info("✅ Changes pushed to GitHub")
            else:
                result["errors"].append("Failed to push changes to GitHub")
                logger.error("❌ Failed to push to GitHub")
        elif dry_run:
            logger.info("DRY RUN: Skipping commit/push")
        
        # Set status based on errors
        if result["errors"]:
            result["status"] = "partial_success" if result["synced_files"] else "failed"
        
    except Exception as e:
        logger.error(f"Context sync job failed: {e}", exc_info=True)
        result["status"] = "failed"
        result["errors"].append(str(e))
    
    # Calculate duration
    end_time = datetime.now()
    result["duration_seconds"] = (end_time - start_time).total_seconds()
    
    logger.info(f"Context sync job completed: {result['status']} in {result['duration_seconds']:.2f}s")
    return result


# For direct testing
if __name__ == "__main__":
    import asyncio
    
    # Run with dry_run=True for testing
    result = asyncio.run(run_context_sync(dry_run=True))
    print(f"\nSync Result: {result}")

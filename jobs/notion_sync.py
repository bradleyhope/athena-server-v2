"""
Athena Server v2 - Notion Sync Job
Syncs brain data to Notion as a mirror (one-way: brain → Notion).
Notion is NOT the source of truth - the brain is.
"""

import logging
import os
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import requests

from db.brain import (
    get_brain_status,
    record_notion_sync_time,
    log_notion_sync,
    update_notion_sync_status,
    get_pending_notion_syncs,
    get_core_identity,
    get_boundaries,
    get_values,
    get_workflows,
    get_evolution_proposals,
    get_pending_actions,
)

logger = logging.getLogger("athena.jobs.notion_sync")

# Notion API configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# Target Notion pages/databases for sync
NOTION_TARGETS = {
    "brain_status": "2e5d44b3-a00b-8125-b3dc-cc8c9ee34642",  # ATHENA THINKING page
    "canonical_memory": "2e4d44b3-a00b-810e-9ac1-cbd30e209fab",  # Canonical Memory page
    "evolution_log": None,  # Will be created as needed
}


def notion_request(method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
    """
    Make a request to the Notion API.
    
    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint (without base URL)
        data: Request body data
        
    Returns:
        Response JSON or None on error
    """
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    
    url = f"{NOTION_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Notion API request failed: {e}")
        return None


def format_brain_status_for_notion() -> Dict[str, Any]:
    """
    Format brain status data for Notion page update.
    
    Returns:
        Notion blocks representing the brain status
    """
    status = get_brain_status()
    identity = get_core_identity()
    boundaries = get_boundaries()
    values = get_values()
    workflows = get_workflows()
    pending_actions = get_pending_actions()
    evolution_proposals = get_evolution_proposals()
    
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    # Build content blocks
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Brain 2.0 Status"}}]
            }
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Last synced: {now}\nStatus: {status['status'] if status else 'unknown'}\nVersion: {status['version'] if status else '2.0'}"}}],
                "icon": {"emoji": "🧠"}
            }
        },
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "Identity"}}]
            }
        }
    ]
    
    # Add identity items
    for key, data in identity.items():
        value = data['value']
        if isinstance(value, dict):
            value = json.dumps(value, indent=2)
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"{key}: ", "annotations": {"bold": True}}},
                    {"type": "text", "text": {"content": str(value)}}
                ]
            }
        })
    
    # Add boundaries section
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Boundaries ({len(boundaries)})"}}]
        }
    })
    
    for b in boundaries[:5]:  # Limit to first 5
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"[{b['boundary_type']}] ", "annotations": {"bold": True}}},
                    {"type": "text", "text": {"content": b['rule'][:100]}}
                ]
            }
        })
    
    # Add values section
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Values ({len(values)})"}}]
        }
    })
    
    for v in values:
        blocks.append({
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"{v['value_name']}: ", "annotations": {"bold": True}}},
                    {"type": "text", "text": {"content": v['description'][:100]}}
                ]
            }
        })
    
    # Add workflows section
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Workflows ({len(workflows)})"}}]
        }
    })
    
    for w in workflows:
        status_emoji = "✅" if w['enabled'] else "⏸️"
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"{status_emoji} {w['workflow_name']} ", "annotations": {"bold": True}}},
                    {"type": "text", "text": {"content": f"({w['trigger_type']}) - {w['description'][:50]}"}}
                ]
            }
        })
    
    # Add pending items section
    if pending_actions or evolution_proposals:
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "Pending Items"}}]
            }
        })
        
        if pending_actions:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"Pending Actions: {len(pending_actions)}"}}]
                }
            })
        
        if evolution_proposals:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"Evolution Proposals: {len(evolution_proposals)}"}}]
                }
            })
    
    return blocks


def sync_brain_status_to_notion() -> bool:
    """
    Sync brain status to the ATHENA THINKING Notion page.
    
    Returns:
        True if sync successful
    """
    page_id = NOTION_TARGETS.get("brain_status")
    if not page_id:
        logger.warning("No target page configured for brain_status sync")
        return False
    
    logger.info(f"Syncing brain status to Notion page {page_id}...")
    
    try:
        # Get existing page children
        existing = notion_request("GET", f"/blocks/{page_id}/children")
        if not existing:
            logger.error("Failed to fetch existing page content")
            return False
        
        # Delete existing blocks (to replace with new content)
        for block in existing.get("results", []):
            notion_request("DELETE", f"/blocks/{block['id']}")
        
        # Create new blocks
        blocks = format_brain_status_for_notion()
        
        # Notion API limits to 100 blocks per request
        for i in range(0, len(blocks), 100):
            batch = blocks[i:i+100]
            result = notion_request("POST", f"/blocks/{page_id}/children", {"children": batch})
            if not result:
                logger.error(f"Failed to create blocks batch {i//100 + 1}")
                return False
        
        # Log the sync
        log_notion_sync("brain_status", "system", "update", page_id)
        record_notion_sync_time()
        
        logger.info("Brain status synced to Notion successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync brain status to Notion: {e}")
        return False


def sync_evolution_proposals_to_notion() -> bool:
    """
    Sync evolution proposals to Notion for review.
    
    Returns:
        True if sync successful
    """
    proposals = get_evolution_proposals(status='proposed')
    if not proposals:
        logger.info("No evolution proposals to sync")
        return True
    
    logger.info(f"Syncing {len(proposals)} evolution proposals to Notion...")
    
    # For now, we'll append to the ATHENA THINKING page
    # In the future, this could be a dedicated database
    page_id = NOTION_TARGETS.get("brain_status")
    if not page_id:
        return False
    
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Evolution Proposals for Review"}}]
            }
        }
    ]
    
    for p in proposals:
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"{p['evolution_type']}: {p['description']}\n"}},
                    {"type": "text", "text": {"content": f"Category: {p['category']} | Confidence: {p['confidence']:.0%}\n", "annotations": {"italic": True}}},
                    {"type": "text", "text": {"content": f"Source: {p['source']}", "annotations": {"italic": True}}}
                ],
                "icon": {"emoji": "🔄"}
            }
        })
    
    result = notion_request("POST", f"/blocks/{page_id}/children", {"children": blocks})
    return result is not None


async def run_notion_sync():
    """
    Main Notion sync job.
    Runs periodically to sync brain state to Notion mirror.
    """
    logger.info("Starting Notion sync job...")
    
    # Check if sync is enabled
    status = get_brain_status()
    if not status:
        logger.warning("Brain status not found, skipping sync")
        return
    
    config = status.get('config', {})
    if not config.get('notion_sync_enabled', True):
        logger.info("Notion sync is disabled, skipping")
        return
    
    # Sync brain status
    sync_brain_status_to_notion()
    
    # Sync evolution proposals
    sync_evolution_proposals_to_notion()
    
    logger.info("Notion sync job completed")


# Manual sync function for testing
def manual_sync():
    """Run sync manually for testing."""
    import asyncio
    asyncio.run(run_notion_sync())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manual_sync()

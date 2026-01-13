"""
Context Loader for GitHub-based Context Injection

Loads context files from the cogos-system repository for injection into
Manus workspace sessions. Provides fast, cacheable access to Bradley's
voice guide, canonical memory, workflows, and preferences.

Performance: <500ms vs Notion's 15-20s
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("athena.context_loader")

# Cache for context files (in-memory, 5-minute TTL)
_context_cache: Dict[str, tuple[str, datetime]] = {}
_cache_ttl = timedelta(minutes=5)

# Path to cogos-system context directory
CONTEXT_DIR = Path("/home/ubuntu/cogos-system/docs/athena/context")


def _load_file(file_path: Path) -> str:
    """Load a markdown file from the context directory."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Context file not found: {file_path}")
        return f"<!-- Context file not found: {file_path} -->"
    except Exception as e:
        logger.error(f"Error loading context file {file_path}: {e}")
        return f"<!-- Error loading context file: {e} -->"


def _get_cached_or_load(cache_key: str, file_path: Path) -> str:
    """Get content from cache or load from file."""
    now = datetime.now()
    
    # Check cache
    if cache_key in _context_cache:
        content, cached_at = _context_cache[cache_key]
        if now - cached_at < _cache_ttl:
            logger.debug(f"Cache hit for {cache_key}")
            return content
    
    # Load from file
    logger.debug(f"Loading {cache_key} from disk")
    content = _load_file(file_path)
    _context_cache[cache_key] = (content, now)
    return content


def load_voice_guide() -> str:
    """Load Bradley's voice and communication style guide."""
    return _get_cached_or_load(
        "voice_guide",
        CONTEXT_DIR / "voice-guide.md"
    )


def load_canonical_memory() -> str:
    """Load canonical memory (user-approved facts and preferences)."""
    return _get_cached_or_load(
        "canonical_memory",
        CONTEXT_DIR / "canonical-memory.md"
    )


def load_vip_contacts() -> str:
    """Load VIP contacts list."""
    return _get_cached_or_load(
        "vip_contacts",
        CONTEXT_DIR / "vip-contacts.md"
    )


def load_preferences() -> str:
    """Load learned preferences."""
    return _get_cached_or_load(
        "preferences",
        CONTEXT_DIR / "preferences.md"
    )


def load_policies() -> str:
    """Load policies and boundaries."""
    return _get_cached_or_load(
        "policies",
        CONTEXT_DIR / "policies.md"
    )


def load_workflow(workflow_name: str) -> Optional[str]:
    """
    Load a specific workflow by name.
    
    Args:
        workflow_name: Name of the workflow file (without .md extension)
        
    Returns:
        Workflow content or None if not found
    """
    workflow_path = CONTEXT_DIR / "workflows" / f"{workflow_name}.md"
    if not workflow_path.exists():
        logger.warning(f"Workflow not found: {workflow_name}")
        return None
    
    return _get_cached_or_load(
        f"workflow_{workflow_name}",
        workflow_path
    )


def load_all_workflows() -> Dict[str, str]:
    """
    Load all available workflows.
    
    Returns:
        Dictionary mapping workflow names to their content
    """
    workflows = {}
    workflows_dir = CONTEXT_DIR / "workflows"
    
    if not workflows_dir.exists():
        logger.warning("Workflows directory not found")
        return workflows
    
    for workflow_file in workflows_dir.glob("*.md"):
        if workflow_file.name == "README.md":
            continue
        
        workflow_name = workflow_file.stem
        workflows[workflow_name] = _get_cached_or_load(
            f"workflow_{workflow_name}",
            workflow_file
        )
    
    return workflows


def build_context_injection() -> str:
    """
    Build the complete context injection string for workspace sessions.
    
    This includes:
    - Voice guide
    - Canonical memory
    - VIP contacts
    - Preferences
    - Policies
    - Key workflows
    
    Returns:
        Formatted markdown string with all context
    """
    sections = []
    
    # Voice Guide
    sections.append("## Bradley's Voice & Communication Style\n")
    sections.append(load_voice_guide())
    sections.append("\n---\n")
    
    # Canonical Memory
    sections.append("## Canonical Memory (User-Approved Facts)\n")
    sections.append(load_canonical_memory())
    sections.append("\n---\n")
    
    # VIP Contacts
    sections.append("## VIP Contacts (Require Manual Approval)\n")
    sections.append(load_vip_contacts())
    sections.append("\n---\n")
    
    # Preferences
    sections.append("## Learned Preferences\n")
    sections.append(load_preferences())
    sections.append("\n---\n")
    
    # Policies
    sections.append("## Policies & Boundaries (Hard Constraints)\n")
    sections.append(load_policies())
    sections.append("\n---\n")
    
    # Key Workflows
    sections.append("## Key Workflows\n")
    
    key_workflows = ["email-response", "meeting-prep", "subscriber-thank-you"]
    for workflow_name in key_workflows:
        workflow_content = load_workflow(workflow_name)
        if workflow_content:
            sections.append(f"### {workflow_name.replace('-', ' ').title()}\n")
            sections.append(workflow_content)
            sections.append("\n")
    
    return "".join(sections)


def clear_cache():
    """Clear the context cache (useful for testing or forced refresh)."""
    global _context_cache
    _context_cache.clear()
    logger.info("Context cache cleared")


def get_cache_stats() -> Dict[str, any]:
    """Get cache statistics for monitoring."""
    return {
        "cached_items": len(_context_cache),
        "cache_keys": list(_context_cache.keys()),
        "cache_ttl_seconds": _cache_ttl.total_seconds()
    }


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== Testing Context Loader ===\n")
    
    # Test individual loaders
    print("Loading voice guide...")
    voice = load_voice_guide()
    print(f"Voice guide: {len(voice)} chars\n")
    
    print("Loading canonical memory...")
    memory = load_canonical_memory()
    print(f"Canonical memory: {len(memory)} chars\n")
    
    print("Loading workflows...")
    workflows = load_all_workflows()
    print(f"Found {len(workflows)} workflows: {list(workflows.keys())}\n")
    
    # Test full context injection
    print("Building full context injection...")
    full_context = build_context_injection()
    print(f"Full context: {len(full_context)} chars\n")
    
    # Test cache
    print("Cache stats:", get_cache_stats())

#!/usr/bin/env python3.11
"""
Sync Context to GitHub Script

Syncs data from Neon database to GitHub context files:
- boundaries table → policies.md
- canonical_memory table → canonical-memory.md, vip-contacts.md, preferences.md

This ensures GitHub context files stay up-to-date with database changes.
Run daily via cron or manually after significant database updates.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.neon import db_cursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sync_context")

# Path to cogos-system context directory
CONTEXT_DIR = Path("/home/ubuntu/cogos-system/docs/athena/context")


def get_boundaries_from_db() -> List[Dict]:
    """Fetch all active boundaries from database."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT category, rule, description, boundary_type, requires_approval, created_at
            FROM boundaries
            WHERE active = TRUE
            ORDER BY category, created_at
        """)
        return cursor.fetchall()


def get_canonical_memory_from_db() -> List[Dict]:
    """Fetch all active canonical memory entries from database."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT category, key, value, source, created_at, updated_at
            FROM canonical_memory
            WHERE active = TRUE
            ORDER BY category, created_at
        """)
        return cursor.fetchall()


def format_policies_markdown(boundaries: List[Dict]) -> str:
    """Format boundaries as policies.md markdown."""
    now = datetime.now().isoformat()
    
    # Group boundaries by category
    categories = {}
    for boundary in boundaries:
        category = boundary['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(boundary)
    
    lines = [
        "---",
        'version: "1.0.0"',
        f'last_updated: "{now}"',
        'status: "active"',
        'protection_level: "tier0"',
        'source: "Neon DB boundaries table"',
        'tags: [policies, boundaries, rules, constraints]',
        "---",
        "",
        "# Athena Policies & Boundaries",
        "",
        "**Version:** 1.0  ",
        f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}  ",
        "",
        "> **Purpose:** Hard constraints and policies that govern Athena's autonomous behavior. These are non-negotiable rules that Athena MUST follow.",
        "",
        "---",
        ""
    ]
    
    # Add each category as a section
    for category, items in sorted(categories.items()):
        category_title = category.replace('_', ' ').title()
        lines.append(f"## {category_title} Policies")
        lines.append("")
        lines.append("| Category | Rule | Description | Date Added |")
        lines.append("|----------|------|-------------|------------|")
        
        for item in items:
            date_added = item['created_at'].strftime('%Y-%m-%d') if item['created_at'] else 'N/A'
            rule = item['rule'].replace('|', '\\|')
            description = (item['description'] or '').replace('|', '\\|')
            lines.append(f"| {category} | {rule} | {description} | {date_added} |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.extend([
        "## Notes",
        "",
        "- Policies are synced from Neon DB `boundaries` table",
        "- New policies are added through explicit user instruction or critical incidents",
        "- Violations of policies should trigger immediate alerts to Bradley",
        "",
        "---",
        "",
        "*This page is Tier 0 - Immutable for Athena (READ ONLY). Only Bradley can add or modify policies.*",
        ""
    ])
    
    return "\n".join(lines)


def format_canonical_memory_markdown(entries: List[Dict]) -> str:
    """Format canonical memory entries as canonical-memory.md markdown."""
    now = datetime.now().isoformat()
    
    # Group by category
    categories = {}
    for entry in entries:
        category = entry['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(entry)
    
    lines = [
        "---",
        'version: "1.0.0"',
        f'last_updated: "{now}"',
        'status: "active"',
        'protection_level: "tier0"',
        'source: "Notion page 2e4d44b3-a00b-810e-9ac1-cbd30e209fab + Neon DB canonical_memory table"',
        'tags: [memory, facts, preferences, policies]',
        "---",
        "",
        "# Athena Canonical Memory",
        "",
        "**Version:** 1.0  ",
        f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}  ",
        "",
        "> **Purpose:** User-approved facts that Athena treats as ground truth. These are NOT inferred — they are explicitly confirmed by Bradley.",
        "",
        "---",
        "",
        "## How This Works",
        "",
        "1. Athena proposes memory updates during Tier 3 synthesis",
        "2. Proposals appear in the **Pending Approvals** section below",
        "3. Bradley reviews and approves/rejects in the morning Agenda & Workspace session",
        "4. Approved items move to the appropriate category",
        "5. Athena reads this page at the start of every session",
        "",
        "---",
        ""
    ]
    
    # Add each category as a section
    for category, items in sorted(categories.items()):
        category_title = category.replace('_', ' ').title()
        lines.append(f"## {category_title}")
        lines.append("")
        lines.append("| Key | Value | Source | Date Added |")
        lines.append("|-----|-------|--------|------------|")
        
        for item in items:
            key = item['key'].replace('|', '\\|')
            value = str(item['value']).replace('|', '\\|')
            source = (item['source'] or 'Confirmed').replace('|', '\\|')
            date_added = item['created_at'].strftime('%Y-%m-%d') if item['created_at'] else 'N/A'
            lines.append(f"| {key} | {value} | {source} | {date_added} |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.extend([
        "## Pending Approvals",
        "",
        "> Items proposed by Athena awaiting Bradley approval:",
        "",
        "| Proposed | Category | Content | Status |",
        "|----------|----------|---------|--------|",
        "| (none pending) | | | |",
        "",
        "---",
        "",
        "## Rejected Items",
        "",
        "> Items Bradley explicitly rejected (Athena should not re-propose):",
        "",
        "| Date | Category | Content | Reason |",
        "|------|----------|---------|--------|",
        "| (none) | | | |",
        "",
        "---",
        "",
        "*This page is Tier 0 - Immutable for Athena (READ ONLY). Only Bradley can modify.*",
        ""
    ])
    
    return "\n".join(lines)


def sync_policies():
    """Sync boundaries table to policies.md."""
    logger.info("Syncing policies from boundaries table...")
    
    try:
        boundaries = get_boundaries_from_db()
        logger.info(f"Found {len(boundaries)} active boundaries")
        
        if not boundaries:
            logger.warning("No boundaries found in database, skipping sync")
            return True
        
        markdown = format_policies_markdown(boundaries)
        
        output_path = CONTEXT_DIR / "policies.md"
        
        # Create backup before overwriting
        if output_path.exists():
            backup_path = output_path.with_suffix('.md.backup')
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Write new content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        # Validate
        if not validate_markdown(output_path):
            logger.error("Validation failed, restoring backup")
            if backup_path.exists():
                shutil.copy2(backup_path, output_path)
            return False
        
        logger.info(f"✅ Synced policies to {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to sync policies: {e}")
        return False


def sync_canonical_memory():
    """Sync canonical_memory table to canonical-memory.md."""
    logger.info("Syncing canonical memory from database...")
    
    try:
        entries = get_canonical_memory_from_db()
        logger.info(f"Found {len(entries)} active canonical memory entries")
        
        if not entries:
            logger.warning("No canonical memory entries found, skipping sync")
            return True
        
        markdown = format_canonical_memory_markdown(entries)
        
        output_path = CONTEXT_DIR / "canonical-memory.md"
        
        # Create backup before overwriting
        if output_path.exists():
            backup_path = output_path.with_suffix('.md.backup')
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Write new content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        # Validate
        if not validate_markdown(output_path):
            logger.error("Validation failed, restoring backup")
            if backup_path.exists():
                shutil.copy2(backup_path, output_path)
            return False
        
        logger.info(f"✅ Synced canonical memory to {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to sync canonical memory: {e}")
        return False


def validate_markdown(file_path: Path) -> bool:
    """Validate that generated markdown is well-formed."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for YAML frontmatter
        if not content.startswith('---'):
            logger.error(f"Missing YAML frontmatter in {file_path}")
            return False
        
        # Check for minimum content length
        if len(content) < 100:
            logger.error(f"Content too short in {file_path}")
            return False
        
        # Check for required sections
        if '# Athena' not in content:
            logger.error(f"Missing main heading in {file_path}")
            return False
        
        logger.debug(f"✅ Validation passed for {file_path}")
        return True
    except Exception as e:
        logger.error(f"Validation failed for {file_path}: {e}")
        return False


def check_git_status():
    """Check if there are changes to commit."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=CONTEXT_DIR.parent.parent.parent,  # cogos-system root
            capture_output=True,
            text=True
        )
        
        changed_files = [line for line in result.stdout.split('\n') if 'docs/athena/context/' in line]
        return changed_files
    except Exception as e:
        logger.error(f"Failed to check git status: {e}")
        return []


def commit_and_push_changes(dry_run: bool = False):
    """Commit and push changes to GitHub."""
    import subprocess
    
    changed_files = check_git_status()
    
    if not changed_files:
        logger.info("No changes to commit")
        return True
    
    logger.info(f"Found {len(changed_files)} changed files:")
    for file in changed_files:
        logger.info(f"  {file}")
    
    if dry_run:
        logger.info("DRY RUN: Would commit and push changes")
        return True
    
    try:
        repo_root = CONTEXT_DIR.parent.parent.parent
        
        # Add changes
        subprocess.run(
            ["git", "add", "docs/athena/context/"],
            cwd=repo_root,
            check=True
        )
        
        # Commit
        commit_msg = f"Auto-sync context from Neon DB - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_root,
            check=True
        )
        
        # Push
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=repo_root,
            check=True
        )
        
        logger.info("✅ Changes committed and pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to commit/push changes: {e}")
        return False


def main():
    """Main sync function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync context from Neon DB to GitHub")
    parser.add_argument('--dry-run', action='store_true', help="Don't commit/push changes")
    parser.add_argument('--no-push', action='store_true', help="Commit but don't push")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Athena Context Sync - Neon DB → GitHub")
    logger.info("=" * 60)
    
    success = True
    
    # Sync policies
    if not sync_policies():
        success = False
    
    # Sync canonical memory
    if not sync_canonical_memory():
        success = False
    
    # Commit and push if not dry run
    if success and not args.dry_run:
        if not args.no_push:
            commit_and_push_changes()
        else:
            logger.info("Skipping push (--no-push flag)")
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Sync completed successfully")
    else:
        logger.error("❌ Sync completed with errors")
    logger.info("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Sync from GitHub to Database

Syncs context file changes from GitHub back to Neon database.
Part of Phase 7: Bidirectional Sync.

Supported files:
- canonical-memory.md → canonical_memory table
- policies.md → boundaries table

Other files (voice-guide, vip-contacts, preferences, workflows) are read-only from GitHub.
"""

import os
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from db.neon import get_connection

logger = logging.getLogger("athena.sync_from_github")

# Path to cogos-system context directory
CONTEXT_DIR = Path("/home/ubuntu/cogos-system/docs/athena/context")


async def sync_from_github(
    changed_files: list[str],
    commit_sha: str,
    commit_message: str,
    commit_author: str,
    commit_timestamp: str
) -> dict:
    """
    Sync changed context files from GitHub to database.
    
    Args:
        changed_files: List of changed file paths (relative to repo root)
        commit_sha: Git commit SHA
        commit_message: Commit message
        commit_author: Commit author name
        commit_timestamp: Commit timestamp (ISO format)
        
    Returns:
        Dict with sync results:
        {
            "synced": [list of synced files],
            "skipped": [list of skipped files],
            "errors": [list of errors]
        }
    """
    results = {
        "synced": [],
        "skipped": [],
        "errors": [],
        "commit_sha": commit_sha,
        "commit_author": commit_author,
        "commit_timestamp": commit_timestamp
    }
    
    # Pull latest changes from GitHub first
    try:
        logger.info("Pulling latest changes from GitHub...")
        pull_result = pull_from_github()
        if not pull_result["success"]:
            logger.error(f"Failed to pull from GitHub: {pull_result['error']}")
            results["errors"].append({
                "file": "git_pull",
                "error": pull_result["error"]
            })
            return results
    except Exception as e:
        logger.error(f"Error pulling from GitHub: {e}")
        results["errors"].append({
            "file": "git_pull",
            "error": str(e)
        })
        return results
    
    # Process each changed file
    for file_path in changed_files:
        try:
            # Determine file type
            filename = Path(file_path).name
            
            logger.info(f"Processing {filename}...")
            
            if filename == "canonical-memory.md":
                result = sync_canonical_memory(commit_sha, commit_author, commit_timestamp)
            elif filename == "policies.md":
                result = sync_policies_with_conflict_resolution(commit_sha, commit_author, commit_timestamp)
            else:
                # Other files are read-only from GitHub
                logger.info(f"Skipping {filename} (read-only from GitHub)")
                results["skipped"].append(file_path)
                continue
            
            if result["success"]:
                results["synced"].append(file_path)
                logger.info(f"Successfully synced {filename}: {result.get('message', '')}")
            else:
                results["errors"].append({
                    "file": file_path,
                    "error": result["error"]
                })
                logger.error(f"Failed to sync {filename}: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error syncing {file_path}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["errors"].append({
                "file": file_path,
                "error": str(e)
            })
    
    return results


def pull_from_github() -> dict:
    """
    Pull latest changes from GitHub repository.
    
    Returns:
        Dict with success status and error message if failed
    """
    import subprocess
    
    try:
        # Change to cogos-system directory
        os.chdir("/home/ubuntu/cogos-system")
        
        # Pull latest changes
        result = subprocess.run(
            ["git", "pull", "origin", "master"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Git pull failed: {result.stderr}"
            }
        
        logger.info(f"Git pull output: {result.stdout}")
        
        return {
            "success": True,
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Git pull timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def sync_canonical_memory(
    commit_sha: str,
    commit_author: str,
    commit_timestamp: str
) -> dict:
    """
    Sync canonical-memory.md to canonical_memory table with conflict resolution.
    
    Conflict Resolution Strategy: Last-write-wins with backup
    - Compare GitHub commit timestamp with database updated_at
    - If GitHub is newer: Update database (with backup)
    - If database is newer: Skip (will sync at 2AM)
    - If within 1 minute: GitHub takes precedence (alert)
    
    Args:
        commit_sha: Git commit SHA
        commit_author: Commit author name
        commit_timestamp: Commit timestamp (ISO format)
        
    Returns:
        Dict with success status and message/error
    """
    try:
        # Read file
        file_path = CONTEXT_DIR / "canonical-memory.md"
        
        if not file_path.exists():
            return {
                "success": False,
                "error": "canonical-memory.md not found"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse markdown (extract entries)
        entries = parse_canonical_memory(content)
        
        if not entries:
            return {
                "success": False,
                "error": "No entries found in canonical-memory.md"
            }
        
        logger.info(f"Parsed {len(entries)} canonical memory entries")
        
        # Parse commit timestamp
        github_timestamp = datetime.fromisoformat(commit_timestamp.replace('Z', '+00:00'))
        
        # Update database with conflict resolution
        conn = get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        inserted_count = 0
        skipped_count = 0
        conflict_count = 0
        
        for entry in entries:
            # Check if entry already exists
            cursor.execute("""
                SELECT id, updated_at FROM canonical_memory
                WHERE category = %s AND content = %s
            """, (entry["category"], entry["content"]))
            
            existing = cursor.fetchone()
            
            if existing:
                existing_id, existing_updated_at = existing
                
                # Conflict resolution: Compare timestamps
                if existing_updated_at:
                    time_diff = abs((github_timestamp - existing_updated_at).total_seconds())
                    
                    if time_diff < 60:
                        # Simultaneous edit (within 1 minute)
                        logger.warning(f"Conflict detected for entry '{entry['content'][:50]}...' (time diff: {time_diff}s)")
                        conflict_count += 1
                        # GitHub takes precedence
                    elif existing_updated_at > github_timestamp:
                        # Database is newer, skip
                        logger.info(f"Skipping entry '{entry['content'][:50]}...' (database is newer)")
                        skipped_count += 1
                        continue
                
                # Create backup before updating
                create_backup(cursor, 'canonical_memory', existing_id)
                
                # Update existing entry
                cursor.execute("""
                    UPDATE canonical_memory
                    SET updated_at = %s, source = %s
                    WHERE id = %s
                """, (github_timestamp, f"github_sync:{commit_sha[:7]}", existing_id))
                updated_count += 1
            else:
                # Insert new entry
                cursor.execute("""
                    INSERT INTO canonical_memory (category, content, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    entry["category"],
                    entry["content"],
                    f"github_sync:{commit_sha[:7]}",
                    github_timestamp,
                    github_timestamp
                ))
                inserted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        message = f"Synced {len(entries)} entries ({inserted_count} inserted, {updated_count} updated, {skipped_count} skipped)"
        if conflict_count > 0:
            message += f" - {conflict_count} conflicts resolved (GitHub took precedence)"
        
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error syncing canonical memory: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }


def sync_policies(
    commit_sha: str,
    commit_author: str,
    commit_timestamp: str
) -> dict:
    """
    Sync policies.md to boundaries table.
    
    Args:
        commit_sha: Git commit SHA
        commit_author: Commit author name
        commit_timestamp: Commit timestamp (ISO format)
        
    Returns:
        Dict with success status and message/error
    """
    try:
        # Read file
        file_path = CONTEXT_DIR / "policies.md"
        
        if not file_path.exists():
            return {
                "success": False,
                "error": "policies.md not found"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse markdown (extract policies)
        policies = parse_policies(content)
        
        if not policies:
            return {
                "success": False,
                "error": "No policies found in policies.md"
            }
        
        logger.info(f"Parsed {len(policies)} policies")
        
        # Update database
        conn = get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        inserted_count = 0
        
        for policy in policies:
            # Check if policy already exists
            cursor.execute("""
                SELECT id, updated_at FROM boundaries
                WHERE category = %s AND rule = %s
            """, (policy["category"], policy["rule"]))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing policy
                cursor.execute("""
                    UPDATE boundaries
                    SET severity = %s, updated_at = %s, source = %s
                    WHERE id = %s
                """, (
                    policy["severity"],
                    commit_timestamp,
                    f"github_sync:{commit_sha[:7]}",
                    existing[0]
                ))
                updated_count += 1
            else:
                # Insert new policy
                cursor.execute("""
                    INSERT INTO boundaries (category, rule, severity, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    policy["category"],
                    policy["rule"],
                    policy["severity"],
                    f"github_sync:{commit_sha[:7]}",
                    commit_timestamp,
                    commit_timestamp
                ))
                inserted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": f"Synced {len(policies)} policies ({inserted_count} inserted, {updated_count} updated)"
        }
        
    except Exception as e:
        logger.error(f"Error syncing policies: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }


def parse_canonical_memory(content: str) -> list[dict]:
    """
    Parse canonical-memory.md and extract entries.
    
    Format expected:
    ## Category Name
    
    - Entry 1
    - Entry 2
    
    Args:
        content: Markdown file content
        
    Returns:
        List of dicts with category and content
    """
    entries = []
    current_category = None
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and YAML frontmatter
        if not line or line.startswith('---'):
            continue
        
        # Category header (## Category Name)
        if line.startswith('## '):
            current_category = line[3:].strip()
            continue
        
        # Entry (- Entry text or * Entry text)
        if (line.startswith('- ') or line.startswith('* ')) and current_category:
            entry_text = line[2:].strip()
            
            # Skip empty entries
            if not entry_text:
                continue
            
            entries.append({
                "category": current_category,
                "content": entry_text
            })
    
    return entries


def parse_policies(content: str) -> list[dict]:
    """
    Parse policies.md and extract policies.
    
    Format expected:
    ## Category Name
    
    - **[Severity]** Policy rule text
    
    Args:
        content: Markdown file content
        
    Returns:
        List of dicts with category, rule, and severity
    """
    policies = []
    current_category = None
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and YAML frontmatter
        if not line or line.startswith('---'):
            continue
        
        # Category header (## Category Name)
        if line.startswith('## '):
            current_category = line[3:].strip()
            continue
        
        # Policy entry (- **[Severity]** Policy text)
        if (line.startswith('- ') or line.startswith('* ')) and current_category:
            entry_text = line[2:].strip()
            
            # Extract severity and rule
            # Format: **[CRITICAL]** Rule text or **[WARNING]** Rule text
            severity_match = re.match(r'\*\*\[(.*?)\]\*\*\s*(.*)', entry_text)
            
            if severity_match:
                severity = severity_match.group(1).lower()
                rule = severity_match.group(2).strip()
            else:
                # No severity specified, default to "normal"
                severity = "normal"
                rule = entry_text
            
            # Skip empty rules
            if not rule:
                continue
            
            policies.append({
                "category": current_category,
                "rule": rule,
                "severity": severity
            })
    
    return policies


# For testing
if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== Testing Sync from GitHub ===\n")
    
    # Test parsing canonical memory
    print("Testing canonical memory parsing...")
    test_content = """
---
version: "1.0.0"
---

## Personal Information

- Bradley Hope is a journalist and author
- Lives in London, UK

## Work Preferences

- Prefers morning meetings (9-11 AM)
- Deep work time: Friday afternoons
"""
    
    entries = parse_canonical_memory(test_content)
    print(f"Parsed {len(entries)} entries:")
    for entry in entries:
        print(f"  - {entry['category']}: {entry['content']}")
    
    print("\nTesting policies parsing...")
    test_policies = """
---
version: "1.0.0"
---

## Email Communication

- **[CRITICAL]** Never send emails to VIP contacts without approval
- **[WARNING]** Always check VIP list before sending

## Calendar Management

- Protect Friday afternoons for deep work
"""
    
    policies = parse_policies(test_policies)
    print(f"Parsed {len(policies)} policies:")
    for policy in policies:
        print(f"  - [{policy['severity'].upper()}] {policy['category']}: {policy['rule']}")


def create_backup(cursor, table_name: str, record_id: int):
    """
    Create backup of a record before updating.
    
    Stores backup in context_sync_backups table for audit trail.
    
    Args:
        cursor: Database cursor
        table_name: Name of the table being updated
        record_id: ID of the record being updated
    """
    try:
        # Create backups table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_sync_backups (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                record_id INTEGER NOT NULL,
                backup_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Get current record data
        if table_name == 'canonical_memory':
            cursor.execute("""
                SELECT id, category, content, source, created_at, updated_at
                FROM canonical_memory WHERE id = %s
            """, (record_id,))
        elif table_name == 'boundaries':
            cursor.execute("""
                SELECT id, category, rule, severity, source, created_at, updated_at
                FROM boundaries WHERE id = %s
            """, (record_id,))
        else:
            logger.warning(f"Unknown table for backup: {table_name}")
            return
        
        record = cursor.fetchone()
        if not record:
            logger.warning(f"Record {record_id} not found in {table_name}")
            return
        
        # Convert to dict
        if table_name == 'canonical_memory':
            backup_data = {
                "id": record[0],
                "category": record[1],
                "content": record[2],
                "source": record[3],
                "created_at": record[4].isoformat() if record[4] else None,
                "updated_at": record[5].isoformat() if record[5] else None
            }
        elif table_name == 'boundaries':
            backup_data = {
                "id": record[0],
                "category": record[1],
                "rule": record[2],
                "severity": record[3],
                "source": record[4],
                "created_at": record[5].isoformat() if record[5] else None,
                "updated_at": record[6].isoformat() if record[6] else None
            }
        
        # Store backup
        import json
        cursor.execute("""
            INSERT INTO context_sync_backups (table_name, record_id, backup_data)
            VALUES (%s, %s, %s)
        """, (table_name, record_id, json.dumps(backup_data)))
        
        logger.debug(f"Created backup for {table_name}.{record_id}")
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        # Don't fail the sync if backup fails, just log it


def sync_policies_with_conflict_resolution(
    commit_sha: str,
    commit_author: str,
    commit_timestamp: str
) -> dict:
    """
    Sync policies.md to boundaries table with conflict resolution.
    
    Conflict Resolution Strategy: Last-write-wins with backup
    - Compare GitHub commit timestamp with database updated_at
    - If GitHub is newer: Update database (with backup)
    - If database is newer: Skip (will sync at 2AM)
    - If within 1 minute: GitHub takes precedence (alert)
    
    Args:
        commit_sha: Git commit SHA
        commit_author: Commit author name
        commit_timestamp: Commit timestamp (ISO format)
        
    Returns:
        Dict with success status and message/error
    """
    try:
        # Read file
        file_path = CONTEXT_DIR / "policies.md"
        
        if not file_path.exists():
            return {
                "success": False,
                "error": "policies.md not found"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse markdown (extract policies)
        policies = parse_policies(content)
        
        if not policies:
            return {
                "success": False,
                "error": "No policies found in policies.md"
            }
        
        logger.info(f"Parsed {len(policies)} policies")
        
        # Parse commit timestamp
        github_timestamp = datetime.fromisoformat(commit_timestamp.replace('Z', '+00:00'))
        
        # Update database with conflict resolution
        conn = get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        inserted_count = 0
        skipped_count = 0
        conflict_count = 0
        
        for policy in policies:
            # Check if policy already exists
            cursor.execute("""
                SELECT id, updated_at FROM boundaries
                WHERE category = %s AND rule = %s
            """, (policy["category"], policy["rule"]))
            
            existing = cursor.fetchone()
            
            if existing:
                existing_id, existing_updated_at = existing
                
                # Conflict resolution: Compare timestamps
                if existing_updated_at:
                    time_diff = abs((github_timestamp - existing_updated_at).total_seconds())
                    
                    if time_diff < 60:
                        # Simultaneous edit (within 1 minute)
                        logger.warning(f"Conflict detected for policy '{policy['rule'][:50]}...' (time diff: {time_diff}s)")
                        conflict_count += 1
                        # GitHub takes precedence
                    elif existing_updated_at > github_timestamp:
                        # Database is newer, skip
                        logger.info(f"Skipping policy '{policy['rule'][:50]}...' (database is newer)")
                        skipped_count += 1
                        continue
                
                # Create backup before updating
                create_backup(cursor, 'boundaries', existing_id)
                
                # Update existing policy
                cursor.execute("""
                    UPDATE boundaries
                    SET severity = %s, updated_at = %s, source = %s
                    WHERE id = %s
                """, (
                    policy["severity"],
                    github_timestamp,
                    f"github_sync:{commit_sha[:7]}",
                    existing_id
                ))
                updated_count += 1
            else:
                # Insert new policy
                cursor.execute("""
                    INSERT INTO boundaries (category, rule, severity, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    policy["category"],
                    policy["rule"],
                    policy["severity"],
                    f"github_sync:{commit_sha[:7]}",
                    github_timestamp,
                    github_timestamp
                ))
                inserted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        message = f"Synced {len(policies)} policies ({inserted_count} inserted, {updated_count} updated, {skipped_count} skipped)"
        if conflict_count > 0:
            message += f" - {conflict_count} conflicts resolved (GitHub took precedence)"
        
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error syncing policies: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

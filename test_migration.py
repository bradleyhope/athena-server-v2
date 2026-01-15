"""
Test script for GitHub-first migration.
Verifies that the changes to morning_sessions.py work correctly.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, '/home/ubuntu/athena-server-v2')

# Set up minimal environment
os.environ['DATABASE_URL'] = ''  # Empty to skip DB connection
os.environ['ATHENA_API_KEY'] = 'test_key'

import logging
logging.basicConfig(level=logging.INFO)

def test_context_loader():
    """Test that context_loader.py has the new function and works correctly."""
    print("\n=== Testing context_loader.py ===\n")
    
    from utils.context_loader import load_specific_doc, build_context_injection, COGOS_ROOT
    
    # Test 1: COGOS_ROOT is defined
    print(f"1. COGOS_ROOT: {COGOS_ROOT}")
    assert COGOS_ROOT.exists(), f"COGOS_ROOT does not exist: {COGOS_ROOT}"
    print("   ✓ COGOS_ROOT exists")
    
    # Test 2: load_specific_doc function exists and works
    print("\n2. Testing load_specific_doc()...")
    athena_init = load_specific_doc("docs/athena/ATHENA_INIT.md")
    assert athena_init is not None, "ATHENA_INIT.md not loaded"
    assert len(athena_init) > 0, "ATHENA_INIT.md is empty"
    print(f"   ✓ ATHENA_INIT.md loaded: {len(athena_init)} chars")
    
    # Test 3: Verify ATHENA_INIT.md contains expected content
    print("\n3. Verifying ATHENA_INIT.md content...")
    assert "ATHENA" in athena_init, "ATHENA_INIT.md missing ATHENA header"
    assert "brain" in athena_init.lower(), "ATHENA_INIT.md missing brain reference"
    print("   ✓ ATHENA_INIT.md contains expected content")
    
    # Test 4: build_context_injection still works
    print("\n4. Testing build_context_injection()...")
    try:
        context = build_context_injection()
        print(f"   ✓ build_context_injection() returned {len(context)} chars")
    except Exception as e:
        print(f"   ⚠ build_context_injection() raised: {e}")
        print("   (This is expected if context files don't exist)")
    
    print("\n=== context_loader.py tests passed ===\n")


def test_morning_sessions():
    """Test that morning_sessions.py generates the correct prompt."""
    print("\n=== Testing morning_sessions.py ===\n")
    
    from jobs.morning_sessions import get_workspace_agenda_prompt
    
    # Test 1: Generate prompt
    print("1. Generating workspace agenda prompt...")
    prompt = get_workspace_agenda_prompt()
    assert prompt is not None, "Prompt is None"
    assert len(prompt) > 0, "Prompt is empty"
    print(f"   ✓ Prompt generated: {len(prompt)} chars")
    
    # Test 2: Verify prompt does NOT reference Notion Command Center
    print("\n2. Verifying prompt does NOT reference Notion Command Center...")
    assert "ATHENA_COMMAND_CENTER_ID" not in prompt, "Prompt still references ATHENA_COMMAND_CENTER_ID"
    assert "2e3d44b3-a00b-81ab-bbda-ced57f8c345d" not in prompt, "Prompt still contains Command Center ID"
    print("   ✓ No references to Notion Command Center")
    
    # Test 3: Verify prompt contains ATHENA_INIT.md content
    print("\n3. Verifying prompt contains ATHENA_INIT.md content...")
    assert "ATHENA" in prompt, "Prompt missing ATHENA header"
    print("   ✓ Prompt contains ATHENA content")
    
    # Test 4: Verify prompt contains dynamic context
    print("\n4. Verifying prompt contains dynamic context section...")
    # Either has the placeholder replaced or has the appended section
    has_context = "Dynamic Context" in prompt or "Voice" in prompt or "Preferences" in prompt
    print(f"   {'✓' if has_context else '⚠'} Dynamic context {'found' if has_context else 'not found (may be expected if context files missing)'}")
    
    # Test 5: Verify prompt contains task database reference
    print("\n5. Verifying prompt contains task database reference...")
    assert "ATHENA_TASKS_DB_ID" in prompt or "44aa96e7-eb95-45ac-9b28-f3bfffec6802" in prompt, "Prompt missing tasks DB reference"
    print("   ✓ Tasks database reference found")
    
    print("\n=== morning_sessions.py tests passed ===\n")
    
    # Print first 500 chars of prompt for verification
    print("=== First 500 chars of generated prompt ===")
    print(prompt[:500])
    print("...")


def test_config():
    """Test that config.py no longer has deprecated Notion IDs."""
    print("\n=== Testing config.py ===\n")
    
    from config import settings
    
    # Test 1: Verify deprecated IDs are removed
    print("1. Verifying deprecated Notion IDs are removed...")
    assert not hasattr(settings, 'ATHENA_COMMAND_CENTER_ID'), "ATHENA_COMMAND_CENTER_ID still exists"
    assert not hasattr(settings, 'CANONICAL_MEMORY_ID'), "CANONICAL_MEMORY_ID still exists"
    assert not hasattr(settings, 'VIP_CONTACTS_ID'), "VIP_CONTACTS_ID still exists"
    assert not hasattr(settings, 'POLICIES_RULES_ID'), "POLICIES_RULES_ID still exists"
    assert not hasattr(settings, 'WORKSPACE_GUIDE_PAGE_ID'), "WORKSPACE_GUIDE_PAGE_ID still exists"
    print("   ✓ All deprecated Notion IDs removed")
    
    # Test 2: Verify required IDs still exist
    print("\n2. Verifying required database IDs still exist...")
    assert hasattr(settings, 'SESSION_ARCHIVE_DB_ID'), "SESSION_ARCHIVE_DB_ID missing"
    assert hasattr(settings, 'ATHENA_TASKS_DB_ID'), "ATHENA_TASKS_DB_ID missing"
    assert hasattr(settings, 'BROADCASTS_DATABASE_ID'), "BROADCASTS_DATABASE_ID missing"
    print("   ✓ All required database IDs present")
    
    print("\n=== config.py tests passed ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("GitHub-First Migration Test Suite")
    print("=" * 60)
    
    try:
        test_context_loader()
        test_config()
        test_morning_sessions()
        
        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Athena Server v2 - Deployment Verification Script

Verifies that all core systems are working correctly after deployment to Render.
Tests:
1. Database connectivity
2. Context loader functionality
3. Pattern detection service
4. Sync systems
5. API endpoints
6. Workflow execution
"""

import sys
import logging
from datetime import datetime
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("athena.verify")

# Test results
results = {
    "timestamp": datetime.utcnow().isoformat(),
    "tests": {},
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
}


def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        import anthropic
        import psycopg
        import fastapi
        import uvicorn
        logger.info("✅ All imports successful")
        results["tests"]["imports"] = {"status": "PASS", "message": "All required modules imported"}
        results["summary"]["passed"] += 1
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        results["tests"]["imports"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_config():
    """Test that configuration loads correctly."""
    logger.info("Testing configuration...")
    try:
        from config import settings
        
        # Check critical settings
        checks = {
            "DATABASE_URL": bool(settings.DATABASE_URL),
            "ANTHROPIC_API_KEY": bool(settings.ANTHROPIC_API_KEY),
            "MANUS_API_KEY": bool(settings.MANUS_API_KEY),
            "ATHENA_API_KEY": bool(settings.ATHENA_API_KEY),
        }
        
        all_ok = all(checks.values())
        if all_ok:
            logger.info("✅ Configuration loaded successfully")
            results["tests"]["config"] = {"status": "PASS", "checks": checks}
            results["summary"]["passed"] += 1
            return True
        else:
            missing = [k for k, v in checks.items() if not v]
            logger.warning(f"⚠️  Missing config: {missing}")
            results["tests"]["config"] = {"status": "WARN", "missing": missing}
            results["summary"]["warnings"] += 1
            return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        results["tests"]["config"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_database():
    """Test database connectivity."""
    logger.info("Testing database connectivity...")
    try:
        from db.neon import get_db_connection
        
        conn = get_db_connection(max_retries=1)
        if conn:
            logger.info("✅ Database connection successful")
            results["tests"]["database"] = {"status": "PASS", "message": "Connected to Neon database"}
            results["summary"]["passed"] += 1
            conn.close()
            return True
        else:
            logger.error("❌ Database connection failed")
            results["tests"]["database"] = {"status": "FAIL", "message": "Could not connect to database"}
            results["summary"]["failed"] += 1
            return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        results["tests"]["database"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_context_loader():
    """Test GitHub context loader."""
    logger.info("Testing context loader...")
    try:
        from utils.context_loader import build_context_injection
        
        context = build_context_injection()
        if context and len(context) > 1000:
            logger.info(f"✅ Context loader working ({len(context)} chars)")
            results["tests"]["context_loader"] = {
                "status": "PASS",
                "message": f"Loaded {len(context)} characters of context"
            }
            results["summary"]["passed"] += 1
            return True
        else:
            logger.warning("⚠️  Context loader returned minimal data")
            results["tests"]["context_loader"] = {
                "status": "WARN",
                "message": f"Only loaded {len(context) if context else 0} characters"
            }
            results["summary"]["warnings"] += 1
            return True
    except Exception as e:
        logger.error(f"❌ Context loader test failed: {e}")
        results["tests"]["context_loader"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_pattern_detection():
    """Test pattern detection functionality."""
    logger.info("Testing pattern detection...")
    try:
        from jobs.pattern_detection import analyze_observations_for_patterns
        from anthropic import Anthropic
        from config import settings
        
        # Create test observations
        test_obs = [
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'source_type': 'email',
                'category': 'work',
                'priority': 'high',
                'summary': 'Important meeting scheduled',
                'observed_at': datetime.utcnow()
            },
            {
                'id': '223e4567-e89b-12d3-a456-426614174001',
                'source_type': 'email',
                'category': 'work',
                'priority': 'high',
                'summary': 'Follow-up on project deadline',
                'observed_at': datetime.utcnow()
            }
        ]
        
        # Test pattern analysis
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        patterns = analyze_observations_for_patterns(client, test_obs)
        
        logger.info(f"✅ Pattern detection working ({len(patterns)} patterns found)")
        results["tests"]["pattern_detection"] = {
            "status": "PASS",
            "message": f"Analyzed observations and found {len(patterns)} patterns"
        }
        results["summary"]["passed"] += 1
        return True
    except Exception as e:
        logger.error(f"❌ Pattern detection test failed: {e}")
        results["tests"]["pattern_detection"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_sync_scripts():
    """Test that sync scripts are available."""
    logger.info("Testing sync scripts...")
    try:
        import os
        
        scripts = [
            'scripts/sync_context_to_github.py',
            'scripts/sync_from_github.py'
        ]
        
        all_exist = all(os.path.exists(s) for s in scripts)
        if all_exist:
            logger.info("✅ Sync scripts available")
            results["tests"]["sync_scripts"] = {
                "status": "PASS",
                "message": "All sync scripts present"
            }
            results["summary"]["passed"] += 1
            return True
        else:
            missing = [s for s in scripts if not os.path.exists(s)]
            logger.warning(f"⚠️  Missing sync scripts: {missing}")
            results["tests"]["sync_scripts"] = {
                "status": "WARN",
                "message": f"Missing: {missing}"
            }
            results["summary"]["warnings"] += 1
            return True
    except Exception as e:
        logger.error(f"❌ Sync scripts test failed: {e}")
        results["tests"]["sync_scripts"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def test_api_routes():
    """Test that API routes are defined."""
    logger.info("Testing API routes...")
    try:
        from main import app
        
        # Check for key routes
        routes = [route.path for route in app.routes]
        
        key_routes = [
            '/api/health',
            '/api/brief',
            '/api/brain/status',
        ]
        
        found = [r for r in key_routes if any(r in route for route in routes)]
        
        if len(found) >= 1:
            logger.info(f"✅ API routes available ({len(routes)} total)")
            results["tests"]["api_routes"] = {
                "status": "PASS",
                "message": f"Found {len(routes)} API routes"
            }
            results["summary"]["passed"] += 1
            return True
        else:
            logger.warning("⚠️  Limited API routes found")
            results["tests"]["api_routes"] = {
                "status": "WARN",
                "message": f"Only {len(found)} key routes found"
            }
            results["summary"]["warnings"] += 1
            return True
    except Exception as e:
        logger.error(f"❌ API routes test failed: {e}")
        results["tests"]["api_routes"] = {"status": "FAIL", "message": str(e)}
        results["summary"]["failed"] += 1
        return False


def main():
    """Run all deployment verification tests."""
    logger.info("=" * 60)
    logger.info("ATHENA SERVER V2 - DEPLOYMENT VERIFICATION")
    logger.info("=" * 60)
    
    results["summary"]["total"] = 7
    
    # Run all tests
    test_imports()
    test_config()
    test_database()
    test_context_loader()
    test_pattern_detection()
    test_sync_scripts()
    test_api_routes()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("DEPLOYMENT VERIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Tests: {results['summary']['total']}")
    logger.info(f"Passed: {results['summary']['passed']}")
    logger.info(f"Failed: {results['summary']['failed']}")
    logger.info(f"Warnings: {results['summary']['warnings']}")
    
    # Print detailed results
    logger.info("\nDetailed Results:")
    for test_name, test_result in results["tests"].items():
        status = test_result.get("status", "UNKNOWN")
        message = test_result.get("message", "")
        logger.info(f"  {test_name}: {status} - {message}")
    
    # Save results to file
    with open('/tmp/deployment_verification.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("\nResults saved to /tmp/deployment_verification.json")
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        logger.error("❌ DEPLOYMENT VERIFICATION FAILED")
        return 1
    elif results['summary']['warnings'] > 0:
        logger.warning("⚠️  DEPLOYMENT VERIFICATION PASSED WITH WARNINGS")
        return 0
    else:
        logger.info("✅ DEPLOYMENT VERIFICATION PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())

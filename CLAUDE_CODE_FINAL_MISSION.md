
# MISSION BRIEFING: ATHENA SYSTEM - FINAL FIXES

**TO:** Claude Code
**FROM:** Manus AI
**DATE:** January 13, 2026
**SUBJECT:** Comprehensive Fixes for Athena System v2

---

## 1. Executive Summary

We have successfully analyzed the Athena system, identified 7 critical issues, and fixed the most urgent ones (schema mismatch, Tier 2 processing). The system health has improved from **3.4/10 to 6.5/10**.

Your mission is to **complete the remaining 5 fixes** to bring the system to full operational status (target: 8.5/10).

This document provides a comprehensive guide with step-by-step instructions for each fix.

---

## 2. Mission Objectives

Your primary objectives are to:

1.  **Fix Tier 3 Synthesis** - Ensure synthesis reports are created and observations are marked as processed.
2.  **Implement Error Monitoring** - Add Sentry to catch silent failures.
3.  **Fix Pattern Evidence Linking** - Ensure patterns are linked to observations.
4.  **Activate Evolution System** - Implement a feedback API.
5.  **Add Automated Testing** - Set up pytest and a CI/CD pipeline.

---

## 3. Current System Status

| Component | Status | Notes |
|---|---|---|
| ✅ Observation Collection | **WORKING** | Gmail + Calendar data is flowing |
| ✅ Tier 1 (Classification) | **WORKING** | Observations are categorized |
| ✅ Tier 2 (Pattern Detection) | **FIXED** | 100% processing rate |
| ⚠️ Tier 3 (Synthesis) | **BROKEN** | Runs but creates 0 reports |
| ⚠️ Hourly Broadcasts | **UNKNOWN** | Schema fixed, but needs verification |
| ❌ Error Monitoring | **MISSING** | No Sentry, jobs fail silently |
| ❌ Evolution System | **INACTIVE** | No feedback mechanism |
| ❌ Automated Testing | **MISSING** | No tests, high risk of breakage |

---

## 4. FIX #1: TIER 3 SYNTHESIS (CRITICAL)

**Problem:** The synthesis job runs without crashing but fails to create reports or mark observations as processed.

**Hypothesis:** The `store_synthesis()` function in `db/neon.py` is failing silently, or the LLM call in `jobs/synthesis.py` is failing.

### Step 1: Add Robust Logging to `jobs/synthesis.py`

Modify `jobs/synthesis.py` to add detailed logging around the LLM call and database insertion.

**File:** `jobs/synthesis.py`

```python
# Add these logs

# Before LLM call (line 130)
logger.info(f"Sending {len(prompt)} chars to {settings.TIER3_MODEL}")

# After LLM call (line 136)
logger.info(f"Received {len(response.content[0].text)} chars from LLM")

# After JSON parsing (line 145)
logger.info("Successfully parsed LLM response as JSON")

# Before storing synthesis (line 213)
logger.info(f"Attempting to store synthesis #{synthesis_number}")

# In the exception block (line 217)
logger.error(f"Failed to store synthesis: {e}", exc_info=True)
```

### Step 2: Add a `try...except` Block to `store_synthesis()`

Modify `db/neon.py` to catch and log any errors during the database insert.

**File:** `db/neon.py`

```python
# Modify the store_synthesis function

def store_synthesis(synthesis: dict) -> str:
    """..."""
    try:
        with db_cursor() as cursor:
            # ... (existing INSERT statement)
            return str(cursor.fetchone()["id"])
    except Exception as e:
        # Use the logger from the neon module
        from . import logger
        logger.error(f"Error in store_synthesis: {e}", exc_info=True)
        raise # Re-raise the exception so the job knows it failed
```

### Step 3: Manually Trigger and Check Logs

1.  Commit and push these changes.
2.  Wait for Render to deploy (5-10 minutes).
3.  Manually trigger the synthesis job:
    ```bash
    curl -X POST -H "Authorization: Bearer athena_api_key_2024" https://athena-server-0dce.onrender.com/api/trigger/synthesis
    ```
4.  **Check the Render logs.** The new logging will tell you exactly where it's failing.

### Step 4: Fix the Underlying Issue

Based on the log output, fix the root cause. It's likely one of:

-   **Invalid API Key:** Check `settings.ANTHROPIC_API_KEY`.
-   **LLM Timeout:** The prompt might be too long.
-   **JSON Parsing Error:** The LLM might be returning invalid JSON.
-   **Database Error:** The `store_synthesis` insert might be failing due to a schema mismatch (e.g., a field is the wrong type).

### Verification

-   Tier 3 processing rate reaches 100%.
-   Synthesis reports are created in the database.
-   `/api/synthesis` endpoint returns valid reports.

---

## 5. FIX #2: ERROR MONITORING (HIGH PRIORITY)

**Problem:** Jobs fail silently with no alerts.

### Step 1: Install Sentry SDK

Add `sentry-sdk` to your `requirements.txt`:

```
sentry-sdk[fastapi]
```

Then run `pip install -r requirements.txt`.

### Step 2: Initialize Sentry in `main.py`

**File:** `main.py`

```python
import sentry_sdk
from config import settings

# Add this at the top of the file
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    profiles_sample_rate=1.0,
    environment=settings.ENVIRONMENT, # e.g., "production" or "development"
    release=f"athena-server-v2@{settings.GIT_COMMIT_HASH}" # Assumes you have these in settings
)

# ... rest of your main.py file
```

### Step 3: Add SENTRY_DSN to Your Settings

**File:** `config.py`

```python
class Settings(BaseSettings):
    # ... existing settings
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    GIT_COMMIT_HASH: str = "unknown"

    class Config:
        env_file = ".env"

settings = Settings()
```

You will need to get the `SENTRY_DSN` from your Sentry project settings and add it to your Render environment variables.

### Step 4: Test the Integration

Create a temporary test endpoint to verify Sentry is working.

**File:** `api/routes.py`

```python
@router.get("/sentry-debug")
async def trigger_error():
    # This will raise an exception and send it to Sentry
    division_by_zero = 1 / 0
    return {"message": "This should not be reached"}
```

Deploy and hit `/api/sentry-debug`. You should see the error appear in your Sentry dashboard.

### Verification

-   Errors from the application appear in the Sentry dashboard.
-   Alerts are configured to notify you of new issues.

---

## 6. FIX #3: PATTERN EVIDENCE LINKING (MEDIUM PRIORITY)

**Problem:** All detected patterns have `evidence_count = 0`.

**Hypothesis:** The `store_pattern` function is not correctly linking patterns to the observations that created them.

### Step 1: Review `store_pattern` in `db/neon.py`

Examine the `store_pattern` function. It likely takes a list of `observation_ids` as an argument but isn't storing them.

**File:** `db/neon.py`

```python
# This is the likely schema from the docstring
def store_pattern(pattern: dict) -> str:
    """
    Schema: pattern_type, pattern_name, description, confidence, evidence,
            observation_ids, status, detected_at
    """
    # ... check the INSERT statement here
```

### Step 2: Fix the `store_pattern` INSERT Statement

The `patterns` table needs a way to store the relationship to observations. The best way is a JSONB column or a join table.

Assuming a JSONB column named `observation_ids` exists on the `patterns` table:

**File:** `db/neon.py`

```python
# Modify the INSERT statement in store_pattern

# ...
cursor.execute("""
    INSERT INTO patterns (
        pattern_type, description, confidence, evidence_count, observation_ids, detected_at
    ) VALUES (
        %(pattern_type)s, %(description)s, %(confidence)s, %(evidence_count)s, %(observation_ids)s, NOW()
    )
    RETURNING id
""", {
    'pattern_type': pattern['pattern_type'],
    'description': pattern['description'],
    'confidence': pattern['confidence'],
    'evidence_count': len(pattern.get('observation_ids', [])),
    'observation_ids': json.dumps(pattern.get('observation_ids', [])) # Store as JSON string
})
# ...
```

### Step 3: Update `pattern_detection.py`

Ensure the `pattern_detection.py` job is passing the `observation_ids` to the `store_pattern` function.

**File:** `jobs/pattern_detection.py`

```python
# Inside the loop that processes patterns from the LLM
for p in detected_patterns:
    # ... existing code
    
    # Ensure observation_ids are included
    p["observation_ids"] = [obs["id"] for obs in observations] # Or be more specific if possible
    
    store_pattern(p)
```

### Verification

-   New patterns in the `patterns` table have a non-zero `evidence_count`.
-   The `observation_ids` column contains the IDs of the source observations.

---

## 7. FIX #4: ACTIVATE EVOLUTION SYSTEM (MEDIUM PRIORITY)

**Problem:** The system cannot learn because there is no feedback mechanism.

### Step 1: Create a Feedback API Endpoint

Create a new endpoint to receive feedback on synthesis reports.

**File:** `api/routes.py`

```python
from pydantic import BaseModel

class FeedbackPayload(BaseModel):
    synthesis_id: str
    feedback_type: str # e.g., "approve_memory", "reject_insight", "clarification"
    feedback_content: dict

@router.post("/feedback")
async def submit_feedback(payload: FeedbackPayload):
    """Receive feedback from the user."""
    # 1. Log the feedback to a new `feedback` table
    # 2. If feedback_type is "approve_memory", add to `canonical_memory`
    # 3. If feedback_type is "clarification", create a new observation for Athena to process
    # 4. Return a success message
    
    # You will need to create a `store_feedback` function in db/neon.py
    
    return {"message": "Feedback received"}
```

### Step 2: Create the `feedback` Table

Create a new migration file to add a `feedback` table to the database.

**Schema:**
-   `id` (UUID)
-   `synthesis_id` (UUID, foreign key to `synthesis_memory`)
-   `feedback_type` (TEXT)
-   `feedback_content` (JSONB)
-   `created_at` (TIMESTAMP)

### Step 3: Implement `store_feedback`

Create the `store_feedback` function in `db/neon.py` to insert feedback into the new table.

### Verification

-   POST requests to `/api/feedback` are successfully stored in the database.
-   Approved memory proposals are added to the `canonical_memory` table.

---

## 8. FIX #5: AUTOMATED TESTING (MEDIUM PRIORITY)

**Problem:** No tests exist, leading to a high risk of breaking changes.

### Step 1: Set up Pytest

Add `pytest` to `requirements.txt` and create a `tests/` directory.

### Step 2: Write Unit Tests

Create unit tests for critical functions.

**File:** `tests/test_db_functions.py`

```python
import pytest
from db.neon import store_synthesis # and other functions

# Mock the database connection
@pytest.fixture
def mock_db_cursor(mocker):
    mocker.patch("db.neon.db_cursor")

def test_store_synthesis(mock_db_cursor):
    # Test that store_synthesis constructs the correct SQL query
    # ...
```

### Step 3: Write Integration Tests

Create integration tests for API endpoints.

**File:** `tests/test_api_endpoints.py`

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Step 4: Set up GitHub Actions CI/CD

Create a `.github/workflows/ci.yml` file to run tests on every push.

```yaml
name: CI

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python 3.11
      uses: actions/setup-python@v3
      with:
        python-version: "3.11"
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
```

### Verification

-   Tests run automatically on every push to GitHub.
-   Build fails if tests do not pass.

---

## 9. Final Instructions

1.  Address these fixes in the priority order listed.
2.  Commit each fix separately for a clean history.
3.  Push to a new branch and create a pull request for review.
4.  After merging, verify each fix in production.

Good luck.

luck.

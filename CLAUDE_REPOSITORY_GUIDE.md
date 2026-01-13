# Athena Server v2 Repository Guide for Claude

This document provides a quick reference to help you navigate the athena-server-v2 repository and understand where key files are located.

---

## Repository Structure

```
athena-server-v2/
├── main.py                          # FastAPI server entry point, job scheduler
├── config.py                        # Configuration and environment variables
├── README.md                        # Project overview and Brain 2.0 architecture
│
├── api/                             # API endpoints
│   ├── routes.py                    # Core data endpoints (observations, patterns, synthesis)
│   ├── brain_routes.py              # Brain 2.0 API endpoints
│   ├── auth.py                      # Authentication logic
│   └── ...
│
├── db/                              # Database access layer
│   ├── neon.py                      # Main database functions (store_observation, etc.)
│   └── brain/
│       ├── composite.py             # Brain 2.0 context functions (get_recent_observations)
│       └── ...
│
├── jobs/                            # Scheduled background jobs
│   ├── observation_burst.py         # Collects Gmail/Calendar data (every 30 min)
│   ├── pattern_detection.py         # Detects patterns (every 2 hours)
│   ├── synthesis.py                 # Generates synthesis reports (4x daily)
│   ├── hourly_broadcast.py          # Creates hourly broadcasts
│   └── ...
│
├── migrations/                      # Database schema and migrations
│   ├── brain_2_0_schema.sql         # Brain 2.0 database schema definition
│   └── ...
│
├── docs/                            # Documentation
│   ├── ATHENA_2.0_COMPLETE_ARCHITECTURE.md
│   ├── ATHENA_BRAIN_2.0_ARCHITECTURE.md
│   └── ...
│
└── integrations/                    # External service integrations
    ├── google_auth.py               # Google API authentication
    ├── gmail_client.py              # Gmail API wrapper
    └── manus_api.py                 # Manus task spawning
```

---

## Key Files for the Schema Mismatch Issue

### 1. `db/neon.py`
**Purpose:** Contains all database access functions for the processing pipeline.

**Key Function:**
```python
def store_observation(observation: dict) -> str:
    """
    Store an observation in the database.
    Schema: source_type, source_id, category, priority, requires_action,
            title, summary, raw_metadata, observed_at
    """
```

**What You Need to Know:**
- This file defines the **actual schema** of the `observations` table through its INSERT statement
- The table has columns: `source_type`, `title`, `summary`, `observed_at`, `processed_tier_2`, `processed_tier_3`
- This is the schema used by the processing pipeline

### 2. `db/brain/composite.py`
**Purpose:** Provides context functions for the Brain 2.0 module.

**Key Function:**
```python
def get_recent_observations(limit: int = 10) -> List[Dict]:
    """Get recent observations for context."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT category, content, source, confidence, created_at
            FROM observations
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
```

**What You Need to Know:**
- This file contains the **problematic query** that expects a different schema
- It tries to select columns: `content`, `source`, `confidence`, `created_at`
- These columns **do not exist** in the actual `observations` table
- **This is the file you need to fix**

### 3. `jobs/hourly_broadcast.py`
**Purpose:** Generates hourly thought broadcasts for Bradley.

**Key Function:**
```python
async def generate_thought_burst() -> Dict[str, Any]:
    """Generate a detailed thought burst based on current state."""
    # Get brain context
    brain_status = get_brain_status()
    continuous_state = get_continuous_state_context()  # Calls get_recent_observations
    
    # Get recent observations (last hour)
    recent_observations = continuous_state.get("recent_observations", [])[:5]
```

**What You Need to Know:**
- This job calls `get_continuous_state_context()` which calls `get_recent_observations()`
- When the query fails, it returns an empty list
- This causes broadcasts to report "0 observations"
- **This is the symptom of the problem**

### 4. `migrations/brain_2_0_schema.sql`
**Purpose:** Defines the Brain 2.0 database schema.

**What You Need to Know:**
- This file contains the CREATE TABLE statements for the Brain 2.0 architecture
- It defines tables like `core_identity`, `boundaries`, `values`, `workflows`, etc.
- **It does NOT define the `observations` table**
- This is part of why the schema mismatch exists

---

## Database Information

**Database Type:** PostgreSQL (hosted on Neon)

**Connection:** The `DATABASE_URL` environment variable contains the connection string.

**Access:** All database operations go through the `db_cursor()` context manager in `db/neon.py`.

---

## The Problem in Simple Terms

1. The **processing pipeline** (observation_burst → pattern_detection → synthesis) uses an `observations` table with columns like `title`, `summary`, `source_type`, `observed_at`.

2. The **Brain 2.0 module** (specifically `db/brain/composite.py`) expects an `observations` table with columns like `content`, `source`, `confidence`, `created_at`.

3. These are **the same table** but with **different expected schemas**.

4. When `hourly_broadcast.py` tries to get recent observations, the query in `db/brain/composite.py` fails because the columns don't exist.

5. The failure is silent (returns empty list), so broadcasts report "0 observations".

---

## Your Task

Fix the `get_recent_observations()` function in `db/brain/composite.py` so that it:
1. Queries the **actual columns** that exist in the `observations` table
2. Maps them to the expected format for the Brain 2.0 module
3. Returns data in the same structure as before (so no other code breaks)

You have three approaches to choose from (see `CLAUDE_SCHEMA_DOCUMENTATION.md`):
- **Approach 1:** Modify the query with aliases
- **Approach 2:** Modify the table schema
- **Approach 3:** Create a database view

Choose the approach that best balances speed, maintainability, and architectural cleanliness.

---

## Testing Your Fix

After implementing your fix, you can test it by:

1. **Manual Test:**
   ```bash
   curl -X POST -H "Authorization: Bearer athena_api_key_2024" \
     https://athena-server-0dce.onrender.com/api/trigger/hourly_broadcast
   ```

2. **Check Broadcast:**
   ```bash
   curl -H "Authorization: Bearer athena_api_key_2024" \
     https://athena-server-0dce.onrender.com/api/broadcasts | jq '.broadcasts[0]'
   ```

3. **Verify Observation Count:**
   The broadcast should now show a non-zero `observation_count`.

---

## Additional Resources

- **Full Architecture:** See `docs/ATHENA_2.0_COMPLETE_ARCHITECTURE.md`
- **Brain 2.0 Details:** See `docs/ATHENA_BRAIN_2.0_ARCHITECTURE.md`
- **Schema Details:** See `CLAUDE_SCHEMA_DOCUMENTATION.md` (provided separately)

---

**Good luck with the fix!**

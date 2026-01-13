# Mission Briefing for Claude Code: Fix Athena Schema Mismatch

**Repository:** `bradleyhope/athena-server-v2` (main branch)  
**Your Mission:** Fix a database schema mismatch that's causing the hourly broadcast system to fail  
**Priority:** High - This is blocking a critical feature  
**Estimated Time:** 30-60 minutes

---

## Executive Summary

The Athena system has a database schema mismatch issue. Two different parts of the codebase expect different column names in the same `observations` table. This causes the hourly broadcast system to silently fail and report "0 observations" when there are actually many observations in the database.

**Your task is to fix the query in `db/brain/composite.py` so it works with the actual database schema.**

---

## Background: What is Athena?

Athena is an AI-powered cognitive extension system for Bradley. It:
- Collects data from Gmail and Google Calendar every 30 minutes
- Processes observations through a three-tier thinking model
- Detects patterns and generates synthesis reports
- Sends hourly broadcasts to keep Bradley informed

The system is deployed on Render at `https://athena-server-0dce.onrender.com`.

---

## The Problem in Simple Terms

1. The **processing pipeline** stores observations in a table with columns like:
   - `title`, `summary`, `source_type`, `observed_at`

2. The **Brain 2.0 module** tries to query observations expecting columns like:
   - `content`, `source`, `confidence`, `created_at`

3. These columns **don't exist**, so the query fails silently.

4. The hourly broadcast system uses this query, gets an empty result, and reports "0 observations."

5. This makes the broadcasts useless because they don't include any actual data.

---

## Technical Details

### The Actual Database Schema

The `observations` table (defined implicitly in `db/neon.py`) has these columns:

```sql
CREATE TABLE observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,           -- e.g., "gmail", "calendar"
    source_id TEXT NOT NULL,              -- Original ID from source
    observed_at TIMESTAMP NOT NULL,       -- When collected
    category TEXT,                        -- e.g., "work", "personal"
    priority TEXT,                        -- e.g., "urgent", "normal"
    requires_action BOOLEAN,              -- Action needed?
    title TEXT,                           -- Subject/title
    summary TEXT,                         -- AI-generated summary
    raw_metadata JSONB,                   -- Original data
    processed_tier_2 BOOLEAN DEFAULT FALSE,
    processed_tier_3 BOOLEAN DEFAULT FALSE
);
```

### The Broken Query

In `db/brain/composite.py`, the function `get_recent_observations()` executes:

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
        # ... rest of the function
```

**Problem:** The columns `content`, `source`, `confidence`, and `created_at` don't exist!

### The Impact

The `hourly_broadcast.py` job calls this function:
```python
continuous_state = get_continuous_state_context()  # Calls get_recent_observations
recent_observations = continuous_state.get("recent_observations", [])[:5]
```

When the query fails, it returns `[]`, so broadcasts report "0 observations."

---

## Your Task: Fix the Query

You need to modify the `get_recent_observations()` function in `db/brain/composite.py` to:

1. **Query the actual columns** that exist in the database
2. **Map them to the expected format** so the rest of the code doesn't break
3. **Return data in the same structure** as before

### Recommended Approach: Modify the Query with Aliases

This is the fastest, lowest-risk approach. Update the SQL query to use aliases:

```sql
SELECT 
    category,
    COALESCE(summary, title) AS content,  -- Use summary, fallback to title
    source_type AS source,                -- Map source_type to source
    1.0 AS confidence,                    -- Provide default confidence
    observed_at AS created_at             -- Map observed_at to created_at
FROM observations
ORDER BY observed_at DESC
LIMIT %s
```

**Why this approach?**
- ✅ No database changes required
- ✅ Quick to implement (5 minutes)
- ✅ Low risk - easily reversible
- ✅ Doesn't break any other code

### Alternative Approaches (Read the Docs)

If you prefer a different approach, read `CLAUDE_SCHEMA_DOCUMENTATION.md` in the repository root. It explains:
- **Approach 1:** Modify the query (recommended above)
- **Approach 2:** Modify the table schema (more complex)
- **Approach 3:** Create a database view (hybrid approach)

---

## Step-by-Step Instructions

### Step 1: Open the File
Navigate to `db/brain/composite.py` in the repository.

### Step 2: Find the Function
Locate the `get_recent_observations()` function (around line 50-80).

### Step 3: Update the Query
Replace the SELECT statement with the corrected version that uses aliases to map actual columns to expected names.

**Current (broken) query:**
```sql
SELECT category, content, source, confidence, created_at
FROM observations
ORDER BY created_at DESC
LIMIT %s
```

**Fixed query:**
```sql
SELECT 
    category,
    COALESCE(summary, title) AS content,
    source_type AS source,
    1.0 AS confidence,
    observed_at AS created_at
FROM observations
ORDER BY observed_at DESC
LIMIT %s
```

### Step 4: Test Locally (Optional)
If you have access to the database, you can test the query:
```sql
SELECT 
    category,
    COALESCE(summary, title) AS content,
    source_type AS source,
    1.0 AS confidence,
    observed_at AS created_at
FROM observations
ORDER BY observed_at DESC
LIMIT 5;
```

### Step 5: Commit and Push
```bash
git add db/brain/composite.py
git commit -m "FIX: Update get_recent_observations to use correct column names"
git push origin main
```

### Step 6: Verify Deployment
After Render auto-deploys (5-10 minutes), test the fix:

```bash
# Trigger hourly broadcast
curl -X POST -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/trigger/hourly_broadcast

# Check the latest broadcast
curl -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/broadcasts | jq '.broadcasts[0]'
```

**Expected result:** The broadcast should now show a non-zero `observation_count` and include actual observation data.

---

## Important Files to Review

Before you start, review these files to understand the context:

1. **`CLAUDE_SCHEMA_DOCUMENTATION.md`** (in repo root)
   - Comprehensive explanation of the problem
   - Three potential approaches with trade-offs
   - This is your primary reference document

2. **`CLAUDE_REPOSITORY_GUIDE.md`** (in repo root)
   - Repository structure overview
   - Location of all key files
   - Quick reference guide

3. **`db/brain/composite.py`** (the file you'll edit)
   - Contains the broken `get_recent_observations()` function
   - Line ~50-80

4. **`db/neon.py`** (for reference)
   - Contains `store_observation()` which defines the actual schema
   - Shows what columns actually exist

5. **`jobs/hourly_broadcast.py`** (for reference)
   - Shows how the broken function is being used
   - Helps you understand the impact

---

## Success Criteria

Your fix is successful when:

1. ✅ The code compiles without errors
2. ✅ The `get_recent_observations()` function returns data (not an empty list)
3. ✅ Hourly broadcasts show non-zero observation counts
4. ✅ Broadcasts include actual observation data in the output
5. ✅ No other parts of the system break

---

## What NOT to Do

❌ **Don't modify the database schema** - This is higher risk and not necessary  
❌ **Don't change the return format** - Other code depends on the current structure  
❌ **Don't modify `db/neon.py`** - The processing pipeline is working correctly  
❌ **Don't modify `jobs/hourly_broadcast.py`** - The issue is in the query, not the job  
❌ **Don't create new tables** - We're fixing the existing table query  

---

## Troubleshooting

### If the query still fails after your fix:
1. Check for typos in column names
2. Verify you're using `COALESCE` correctly
3. Make sure the `ORDER BY` uses `observed_at` (not `created_at`)
4. Check that you didn't accidentally break the SQL syntax

### If broadcasts still show "0 observations":
1. Wait 10 minutes for Render to deploy
2. Manually trigger the broadcast via the API
3. Check Render logs for errors
4. Verify the fix was actually deployed (check git commit in logs)

### If you need help:
1. Review `CLAUDE_SCHEMA_DOCUMENTATION.md` for detailed explanations
2. Check the Render logs for error messages
3. Test the SQL query directly in a database client
4. Ask Bradley for clarification

---

## Context: What's Already Been Done

Recent work on the Athena system:

1. ✅ **Fixed Tier 2 Processing** (commit `70f7687`)
   - Pattern detection now marks observations as processed
   - This is working in production

2. ✅ **Fixed Tier 3 Processing** (commit `70f7687`)
   - Synthesis now marks observations as processed
   - **Note:** This appears to NOT be working in production (needs investigation)

3. ✅ **Added Documentation** (commit `7dfb82c`)
   - Created `CLAUDE_SCHEMA_DOCUMENTATION.md`
   - Created `CLAUDE_REPOSITORY_GUIDE.md`
   - These are now in the repository for your reference

4. ❌ **Schema Mismatch NOT Fixed Yet**
   - This is what you're fixing now
   - It's the last major blocker for the broadcast system

---

## Deployment Information

**Platform:** Render.com  
**Service:** athena-server-v2  
**URL:** https://athena-server-0dce.onrender.com  
**Auto-Deploy:** Enabled (watches `main` branch)  
**Deploy Time:** 5-10 minutes after push  

When you push to `main`, Render will automatically:
1. Detect the new commit
2. Build the application
3. Deploy the new version
4. Route traffic to the new instance

You don't need to do anything special - just push to `main`.

---

## Final Checklist

Before you start:
- [ ] Read `CLAUDE_SCHEMA_DOCUMENTATION.md` in the repository
- [ ] Read `CLAUDE_REPOSITORY_GUIDE.md` in the repository
- [ ] Understand the actual vs. expected schema
- [ ] Understand why the query is failing

While working:
- [ ] Open `db/brain/composite.py`
- [ ] Find the `get_recent_observations()` function
- [ ] Update the SQL query with correct column names and aliases
- [ ] Verify the SQL syntax is correct
- [ ] Commit with a clear message

After pushing:
- [ ] Wait 10 minutes for Render to deploy
- [ ] Test the hourly broadcast endpoint
- [ ] Verify broadcasts now show observation data
- [ ] Confirm no other systems broke

---

## Questions You Might Have

**Q: Why not just add the missing columns to the database?**  
A: That's a valid approach (see Approach 2 in the docs), but it's higher risk and requires database migrations. The query fix is faster and safer.

**Q: What if I want to use a different approach?**  
A: Read `CLAUDE_SCHEMA_DOCUMENTATION.md` for alternatives. Approach 3 (database view) is also good.

**Q: Will this break anything else?**  
A: No, as long as you maintain the same return format. The function returns a list of dictionaries with keys: `category`, `content`, `source`, `confidence`, `created_at`.

**Q: How do I test this without deploying?**  
A: If you have database access, you can run the SQL query directly. Otherwise, you'll need to deploy and test in production (it's low risk).

**Q: What if the broadcasts still fail after my fix?**  
A: Check the Render logs for errors. The issue might be elsewhere in the broadcast pipeline.

---

## Your Mission Starts Now

You have all the information you need. The fix should take 5-15 minutes of actual coding time.

**Primary objective:** Fix the `get_recent_observations()` function in `db/brain/composite.py`

**Success metric:** Hourly broadcasts show actual observation data instead of "0 observations"

**Documentation:** Everything is in the repository (`CLAUDE_SCHEMA_DOCUMENTATION.md` and `CLAUDE_REPOSITORY_GUIDE.md`)

**Good luck! 🚀**

---

## Quick Reference

| What | Where | Why |
|------|-------|-----|
| **File to edit** | `db/brain/composite.py` | Contains the broken query |
| **Function to fix** | `get_recent_observations()` | Queries non-existent columns |
| **Actual columns** | `title`, `summary`, `source_type`, `observed_at` | What exists in the database |
| **Expected columns** | `content`, `source`, `confidence`, `created_at` | What the code expects |
| **Fix method** | Use SQL aliases (`AS`) | Map actual → expected |
| **Test endpoint** | `/api/trigger/hourly_broadcast` | Triggers the broadcast job |
| **Verify endpoint** | `/api/broadcasts` | Shows broadcast results |

---

**Document Version:** 1.0  
**Created:** January 13, 2026  
**For:** Claude Code (AI Assistant)  
**By:** Manus AI (System Analysis Agent)

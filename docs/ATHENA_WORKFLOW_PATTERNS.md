# Athena Workflow Patterns & Technical Reference

**Version:** 1.0 | **Date:** January 11, 2026

---

## Documentation Location

All architecture docs are in the GitHub repo:

```bash
gh repo clone bradleyhope/athena-server-v2
cd athena-server-v2/docs/
```

**Files:**
- `ATHENA_BRAIN_2.0_ARCHITECTURE.md` - Full brain architecture
- `ATHENA_2.0_COMPLETE_ARCHITECTURE.md` - Complete system architecture  
- `ATHENA_BRAIN_2.0_HANDOFF.md` - All credentials and implementation roadmap

---

## 1. Think Bursts — How They Should Be Broadcast

### Current State
Think bursts are **NOT currently implemented**. The ATHENA THINKING session runs but doesn't broadcast its thoughts.

### Concept
Athena's THINKING session should periodically update a shared location with her current thoughts, making her reasoning transparent.

### Recommended Implementation

**Option A: Database Table (Recommended)**
```sql
CREATE TABLE thinking_log (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    thought_type VARCHAR(50) NOT NULL,  -- 'observation', 'analysis', 'decision', 'question'
    content TEXT NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Option B: API Endpoint**
```
GET /api/sessions/thinking/status
```
Returns:
```json
{
    "session_id": "XRcYoXZdizZmK3ErrvEHJW",
    "status": "active",
    "current_phase": "pattern_detection",
    "recent_thoughts": [
        {
            "type": "observation",
            "content": "Noticed 3 emails from investors in the last hour",
            "timestamp": "2026-01-11T05:45:00Z"
        }
    ],
    "pending_questions": []
}
```

**Option C: Notion Page (Heavy)**
- Update a dedicated "Athena's Current Thinking" page in real-time
- Pro: Human-readable
- Con: Rate limits, slower

### How ATHENA THINKING Should Use This

```python
# In the ATHENA THINKING session prompt:
"""
Throughout your work, periodically broadcast your thinking:

1. POST to /api/thinking/log with:
   - thought_type: 'observation' | 'analysis' | 'decision' | 'question'
   - content: Your current thought
   - confidence: 0.0-1.0

2. Do this when you:
   - Notice something significant
   - Make a decision
   - Have a question for Bradley
   - Complete a phase of work
"""
```

---

## 2. Proper Way to Use Manus API with Full Context

### Authentication
```
Base URL: https://api.manus.ai/v1
Header: API_KEY (NOT Bearer token)
```

### Creating a Task

```python
import requests

MANUS_API_KEY = "sk-rNTzbonQ9Y0pfVhTicKo6POXtCqfkfM_JhMlmZldLmYv8nyRrj9bINqKl0vs8nnvkuSpJ4unOGA2v4-O"

response = requests.post(
    "https://api.manus.ai/v1/tasks",
    headers={"API_KEY": MANUS_API_KEY},
    json={
        "description": "Your task prompt here",
        "connectors": [
            {"uuid": "d6539e5e-ab95-4ed1-ac1e-c10eb7f79ccf"},  # Gmail
            {"uuid": "66a9f478-89a4-4d87-9f0c-c27f4b49e18d"},  # Google Calendar
            {"uuid": "8f5e3d0f-3e3e-4c3e-9e3e-3e3e3e3e3e3e"},  # Notion
            {"uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},  # GitHub
            {"uuid": "f1e2d3c4-b5a6-7890-fedc-ba0987654321"}   # Google Drive
        ]
    }
)

task = response.json()
print(f"Task URL: https://manus.im/app/{task['id']}")
```

### Connector UUIDs

| Connector | UUID |
|-----------|------|
| Gmail | `d6539e5e-ab95-4ed1-ac1e-c10eb7f79ccf` |
| Google Calendar | `66a9f478-89a4-4d87-9f0c-c27f4b49e18d` |
| Notion | `8f5e3d0f-3e3e-4c3e-9e3e-3e3e3e3e3e3e` |
| GitHub | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Google Drive | `f1e2d3c4-b5a6-7890-fedc-ba0987654321` |
| Outlook Mail | `b2c3d4e5-f6a7-8901-bcde-f23456789012` |
| Outlook Calendar | `c3d4e5f6-a7b8-9012-cdef-345678901234` |
| Stripe | `e5f6a7b8-c9d0-1234-5678-901234567890` |
| Canva | `f6a7b8c9-d0e1-2345-6789-012345678901` |

### Common Mistakes

❌ **Wrong:**
```python
headers={"Authorization": "Bearer sk-..."}  # Wrong header
url = "https://api.manus.im/v1/tasks"       # Wrong domain
connectors=["gmail", "notion"]               # Wrong format - needs UUIDs
```

✅ **Correct:**
```python
headers={"API_KEY": "sk-..."}               # Correct header
url = "https://api.manus.ai/v1/tasks"       # Correct domain
connectors=[{"uuid": "d6539e5e-..."}]       # Correct format
```

---

## 3. Correct Workflow Patterns

### Three Session Architecture

| Session | Time (London) | Trigger | Purpose |
|---------|---------------|---------|---------|
| ATHENA THINKING | 5:30 AM | Server cron → Manus API | Athena's autonomous work |
| Agenda & Workspace | 6:05 AM | Manus scheduled task | Bradley's interactive workspace |
| Athena Architecture | Manual | When needed | Big-picture system work |

### Daily Flow

```
5:30 AM  ┌─────────────────────────────────────────┐
         │ Render cron triggers /api/trigger/      │
         │ morning-sessions                        │
         └──────────────┬──────────────────────────┘
                        │
                        ▼
         ┌─────────────────────────────────────────┐
         │ Server calls Manus API to create        │
         │ ATHENA THINKING session                 │
         └──────────────┬──────────────────────────┘
                        │
                        ▼
         ┌─────────────────────────────────────────┐
         │ ATHENA THINKING session:                │
         │ 1. Reads Command Center (Notion)        │
         │ 2. Fetches data from Athena Server      │
         │ 3. Runs analysis                        │
         │ 4. Stores results                       │
         │ 5. Broadcasts thoughts (future)         │
         └──────────────┬──────────────────────────┘
                        │
6:05 AM                 ▼
         ┌─────────────────────────────────────────┐
         │ Manus scheduled task triggers           │
         │ Agenda & Workspace session              │
         └──────────────┬──────────────────────────┘
                        │
                        ▼
         ┌─────────────────────────────────────────┐
         │ Agenda & Workspace session:             │
         │ 1. Reads Command Center (Notion)        │
         │ 2. Fetches brief from /api/brief        │
         │ 3. Gets calendar (Google Calendar MCP)  │
         │ 4. Checks email (Gmail MCP)             │
         │ 5. Presents daily brief to Bradley      │
         └──────────────┬──────────────────────────┘
                        │
Throughout             ▼
the day   ┌─────────────────────────────────────────┐
          │ Bradley interacts:                      │
          │ - Gives feedback on insights            │
          │ - Answers Athena's questions            │
          │ - Approves/rejects drafts               │
          │ - Requests task execution               │
          │ - Creates new Manus tasks if complex    │
          └─────────────────────────────────────────┘
```

### Architecture Session Flow

```
Manual    ┌─────────────────────────────────────────┐
Trigger   │ Start new Manus session                 │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 1. Read initialization page             │
          │    notion-fetch: 2e5d44b3-a00b-816e-    │
          │    9168-f7c167f1e69e                    │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 2. Clone athena-server-v2               │
          │    gh repo clone bradleyhope/           │
          │    athena-server-v2                     │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 3. Read COMPASS and FORGE               │
          │    notion-fetch: 2e3d44b3-a00b-814e-... │
          │    notion-fetch: 2e3d44b3-a00b-81cc-... │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 4. Log session to Session Archive       │
          │    data_source_id: d075385d-b6f3-472b-  │
          │    b53f-e528f4ed22db                    │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 5. Work on system improvements          │
          │    - Code changes                       │
          │    - Database modifications             │
          │    - Architecture decisions             │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 6. Push changes to GitHub               │
          │    git add . && git commit && git push  │
          └──────────────┬──────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────────┐
          │ 7. Render auto-deploys                  │
          │    (connected to GitHub main branch)    │
          └─────────────────────────────────────────┘
```

---

## Key API Endpoints

### Athena Server (https://athena-server-0dce.onrender.com/api)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server health check |
| `/brief` | GET | Get morning brief |
| `/observations` | GET/POST | Raw observations |
| `/patterns` | GET/POST | Detected patterns |
| `/synthesis` | GET/POST | Tier 3 insights |
| `/drafts` | GET/POST/PUT | Email drafts |
| `/sessions/thinking` | GET | Today's thinking session |
| `/sessions/active` | GET | All active sessions |
| `/trigger/morning-sessions` | POST | Create daily sessions |

### Authentication
```
Header: Authorization: Bearer athena_api_key_2024
```

---

## Key Notion Pages

| Page | ID | Purpose |
|------|-----|---------|
| Command Center | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` | Main instructions |
| Architecture Init | `2e5d44b3-a00b-816e-9168-f7c167f1e69e` | Architecture session setup |
| COGOS | `2e4d44b3-a00b-813b-9ae8-e239ab11eced` | Operating system |
| COMPASS | `2e3d44b3-a00b-814e-83a6-c30e751d6042` | AI planning framework |
| FORGE | `2e3d44b3-a00b-81cc-99c7-cf0892cbeceb` | Multi-agent tools |
| Credentials | `2e2d44b3-a00b-81d1-b1b9-fb2bfd3596aa` | API keys |
| Session Archive | `d075385d-b6f3-472b-b53f-e528f4ed22db` | Session history (database) |

---

## Credentials Quick Reference

### Neon PostgreSQL
```
Host: ep-rough-paper-a4zrxoej-pooler.us-east-1.aws.neon.tech
Database: neondb
User: neondb_owner
Password: npg_tk0Re2adLnbM
SSL: Required
```

### Render API
```
API Key: rnd_Tiw53y9DGLwHQD2BxOFah4NyANvm
Service ID: srv-d5f3t27pm1nc7384fcpg
```

### Manus API
```
Base URL: https://api.manus.ai/v1
Header: API_KEY
Key: sk-rNTzbonQ9Y0pfVhTicKo6POXtCqfkfM_JhMlmZldLmYv8nyRrj9bINqKl0vs8nnvkuSpJ4unOGA2v4-O
```

### Athena Server
```
Base URL: https://athena-server-0dce.onrender.com/api
Header: Authorization: Bearer athena_api_key_2024
```

---

*Document prepared for Athena Architecture sessions*

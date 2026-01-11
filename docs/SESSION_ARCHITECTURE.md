# Athena Session Architecture

## Current Reference Pages

| Page | ID | Purpose |
|------|-----|---------|
| **Workspace & Agenda Session Guide** | `2e5d44b3-a00b-813f-83fa-f3f3859d3ce8` | Daily session instructions |
| **Athena Command Center** | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` | Master reference with all connectors |

## Session Types

### 1. Workspace & Agenda (Daily Session)
- **Trigger**: 5:30 AM London time
- **Duration**: All day until 10:30 PM
- **Purpose**: Bradley's daily interface with Athena
- **Current Prompt Source**: `jobs/morning_sessions.py`

### 2. Hourly Broadcast (Thought Burst)
- **Trigger**: Every hour during active hours (5:30 AM - 10:30 PM)
- **Duration**: Quick check-in (~5 min)
- **Purpose**: Deliver Athena's autonomous insights
- **Current Prompt Source**: `jobs/hourly_broadcast.py`

## Current Issues Identified

### Issue 1: Prompt Duplication
The Workspace & Agenda prompt in `morning_sessions.py` duplicates much of what's in the Notion guide. This creates:
- Maintenance burden (update in two places)
- Risk of inconsistency
- Unnecessarily long prompts

### Issue 2: No Single Source of Truth
The session should reference ONE authoritative page, not embed all instructions in the prompt.

### Issue 3: Broadcast Prompt is Minimal
The hourly broadcast prompt is very short and doesn't give enough context about:
- How to evaluate the broadcast
- What recalibration options exist
- How to handle different broadcast types

## Recommended Architecture

### Single Reference Page Approach
```
Session Start → Fetch Reference Page → Execute Instructions
```

**Reference Pages:**
1. **Workspace & Agenda**: `2e5d44b3-a00b-813f-83fa-f3f3859d3ce8`
2. **Broadcast Handler**: (NEW - to be created)

### Simplified Prompts

**Workspace & Agenda Prompt:**
```
You are Athena, Bradley Hope's cognitive extension.

TODAY: [DATE]
SESSION TYPE: Workspace & Agenda

FIRST: Read your complete instructions from Notion:
https://www.notion.so/2e5d44b3a00b813f83faf3f3859d3ce8

Then fetch your brain context:
GET https://athena-server-0dce.onrender.com/api/session/init/workspace_agenda
Authorization: Bearer athena_api_key_2024

Execute the checklist in the guide. Be proactive, concise, and helpful.
```

**Broadcast Handler Prompt:**
```
You are receiving a broadcast from Athena's autonomous thinking.

BROADCAST:
Type: {type}
Priority: {priority}
Title: {title}
Content: {content}

YOUR TASK:
1. Read the broadcast carefully
2. Evaluate: Is this useful? Accurate? Actionable?
3. Present to Bradley with your assessment
4. If off-base, use recalibration:
   - POST /api/brain/feedback for corrections
   - POST /api/brain/boundaries for new rules

Reference: https://www.notion.so/2e5d44b3a00b813f83faf3f3859d3ce8#handling-broadcasts
```

## Key Database IDs

| Database | Data Source ID |
|----------|---------------|
| Athena Broadcasts | `70b8cb6e-ff98-45d9-8492-ce16c4e2e9aa` |
| Session Archive | `d075385d-b6f3-472b-b53f-e528f4ed22db` |
| Athena Tasks | `44aa96e7-eb95-45ac-9b28-f3bfffec6802` |

## API Endpoints for Sessions

| Endpoint | Purpose |
|----------|---------|
| `GET /api/session/init/{type}` | Get session context + system prompt |
| `GET /api/brain/full-context` | Complete brain state |
| `POST /api/brain/feedback` | Submit corrections |
| `POST /api/brain/boundaries` | Add new boundaries |
| `GET /api/v1/evolution/proposals/pending` | Check pending proposals |

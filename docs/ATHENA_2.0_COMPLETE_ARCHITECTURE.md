# Athena 2.0: Complete System Architecture

**Author:** Manus AI  
**Date:** January 11, 2026  
**Version:** 2.0  
**Status:** Production + Brain 2.0 Proposed

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Core Philosophy](#core-philosophy)
4. [Architecture Diagram](#architecture-diagram)
5. [Component Deep Dive](#component-deep-dive)
   - 5.1 [Athena Server (FastAPI)](#51-athena-server-fastapi)
   - 5.2 [Athena Brain (Neon PostgreSQL)](#52-athena-brain-neon-postgresql)
   - 5.3 [Manus Sessions](#53-manus-sessions)
   - 5.4 [Scheduled Jobs](#54-scheduled-jobs)
   - 5.5 [External Integrations](#55-external-integrations)
6. [Data Flow](#data-flow)
7. [Tiered AI Model System](#tiered-ai-model-system)
8. [Session Types](#session-types)
9. [Security & Access Control](#security--access-control)
10. [Notion Integration](#notion-integration)
11. [Evolution & Learning](#evolution--learning)
12. [API Reference](#api-reference)
13. [Infrastructure](#infrastructure)
14. [Monitoring & Observability](#monitoring--observability)
15. [Disaster Recovery](#disaster-recovery)
16. [Future Roadmap](#future-roadmap)

---

## Executive Summary

Athena 2.0 is a **cognitive extension system** for Bradley Hope that continuously monitors work patterns (emails, calendar, Manus sessions), synthesizes insights using tiered AI models, and either takes action autonomously or surfaces decisions for approval. 

The system operates on a core principle: **Athena doesn't just remind—she either does the work or makes it effortless.**

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Continuous Monitoring** | Polls Gmail, Calendar, and other sources every 15-30 minutes |
| **Tiered Intelligence** | Uses GPT-5 nano (Tier 1), Claude Haiku (Tier 2), Claude Opus (Tier 3) for appropriate tasks |
| **Proactive Synthesis** | Generates daily briefs with actionable insights |
| **Draft Automation** | Creates email drafts for approval, never sends autonomously |
| **Pattern Detection** | Identifies recurring themes, risks, and opportunities |
| **Self-Improvement** | Weekly evolution cycle using highest-tier AI |
| **Session Continuity** | Maintains thinking sessions throughout the day |

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Server** | FastAPI (Python 3.11) on Render |
| **Database** | Neon PostgreSQL (Serverless) |
| **AI Models** | Anthropic Claude, OpenAI GPT, Google Gemini, Grok |
| **Scheduling** | APScheduler + Render Cron Jobs |
| **Agent Runtime** | Manus AI Platform |
| **Integrations** | Gmail, Google Calendar, Notion, GitHub, Stripe, Canva |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ATHENA 2.0 SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         BRADLEY (Human)                              │    │
│  │                                                                      │    │
│  │   • Reviews morning brief                                           │    │
│  │   • Approves/rejects drafts                                         │    │
│  │   • Provides feedback                                               │    │
│  │   • Makes decisions                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    MANUS SESSIONS (Agent Runtime)                    │    │
│  │                                                                      │    │
│  │   ┌─────────────────┐    ┌─────────────────┐                        │    │
│  │   │ ATHENA THINKING │    │ Agenda &        │                        │    │
│  │   │ (6:00 AM)       │    │ Workspace       │                        │    │
│  │   │                 │    │ (6:05 AM)       │                        │    │
│  │   │ Deep analysis   │    │                 │                        │    │
│  │   │ Pattern work    │    │ Daily brief     │                        │    │
│  │   │ Autonomous      │    │ Interactive     │                        │    │
│  │   └─────────────────┘    └─────────────────┘                        │    │
│  │            │                      │                                  │    │
│  │            └──────────┬───────────┘                                  │    │
│  │                       ▼                                              │    │
│  │              17 MCP Connectors                                       │    │
│  │   (Gmail, Calendar, Notion, GitHub, Stripe, Canva, etc.)            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    ATHENA SERVER (FastAPI)                           │    │
│  │                    https://athena-server-0dce.onrender.com           │    │
│  │                                                                      │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │   │  API Routes  │  │  Scheduled   │  │ Integrations │              │    │
│  │   │              │  │  Jobs        │  │              │              │    │
│  │   │ /api/brief   │  │              │  │ • Manus API  │              │    │
│  │   │ /api/brain/* │  │ • Observe    │  │ • Gmail      │              │    │
│  │   │ /api/trigger │  │ • Pattern    │  │ • Calendar   │              │    │
│  │   │ /api/sessions│  │ • Synthesis  │  │ • Notion     │              │    │
│  │   └──────────────┘  │ • Evolution  │  └──────────────┘              │    │
│  │                     └──────────────┘                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    ATHENA BRAIN (Neon PostgreSQL)                    │    │
│  │                                                                      │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │   │   IDENTITY   │  │  KNOWLEDGE   │  │    STATE     │              │    │
│  │   │              │  │              │  │              │              │    │
│  │   │ core_identity│  │ canonical_   │  │ active_      │              │    │
│  │   │ boundaries   │  │ memory       │  │ sessions     │              │    │
│  │   │ values       │  │ workflows    │  │ pending_     │              │    │
│  │   │              │  │ preferences  │  │ items        │              │    │
│  │   │              │  │ entities     │  │ observations │              │    │
│  │   └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  │                                                                      │    │
│  │   ┌──────────────────────────────────────────────────┐              │    │
│  │   │                 EVOLUTION                         │              │    │
│  │   │  evolution_log | performance_metrics | feedback   │              │    │
│  │   └──────────────────────────────────────────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    NOTION (Human-Readable Mirror)                    │    │
│  │                                                                      │    │
│  │   One-way sync: Brain → Notion (never Notion → Brain)               │    │
│  │                                                                      │    │
│  │   • Command Center (documentation)                                   │    │
│  │   • Session Archive (logs)                                          │    │
│  │   • Canonical Memory (mirror)                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Philosophy

### The Three Principles

**1. Brain is Source of Truth**

Athena's knowledge, rules, and state live in her database (Neon PostgreSQL), not in Notion or configuration files. This enables:
- Programmatic control over behavior
- Version-controlled evolution
- No dependency on human-editable documents for core function

**2. Tiered Intelligence**

Not every task needs the most powerful AI. Athena uses the right model for the right job:
- **Tier 1 (GPT-5 nano)**: Fast classification, high volume
- **Tier 2 (Claude Haiku 4.5)**: Pattern detection, moderate reasoning
- **Tier 3 (Claude Opus 4.5)**: Deep synthesis, self-reflection, critical decisions

**3. Appropriate Autonomy**

Athena acts autonomously within defined boundaries, escalates when uncertain:
- **Autonomous**: Observation, classification, pattern detection, drafting
- **Requires Approval**: Sending emails, modifying calendar, canonical memory updates
- **Forbidden**: Deleting data, exceeding budget, VIP actions without approval

---

## Component Deep Dive

### 5.1 Athena Server (FastAPI)

The server is Athena's operational core—it runs scheduled jobs, serves the API, and coordinates all system activity.

**Location:** https://athena-server-0dce.onrender.com  
**Repository:** https://github.com/bradleyhope/athena-server-v2  
**Runtime:** Python 3.11 on Render Web Service

#### Directory Structure

```
athena-server-v2/
├── main.py                 # FastAPI app entry point
├── config.py               # Environment configuration
├── requirements.txt        # Python dependencies
├── api/
│   └── routes.py           # API endpoint definitions
├── db/
│   └── neon.py             # Database operations
├── jobs/
│   ├── observation_burst.py    # Tier 1 observation collection
│   ├── pattern_detection.py    # Tier 2 pattern analysis
│   ├── synthesis.py            # Tier 3 insight generation
│   ├── morning_sessions.py     # Manus session creation
│   └── evolution.py            # Weekly self-improvement (planned)
└── integrations/
    └── manus_api.py        # Manus API client
```

#### Key Features

| Feature | Implementation |
|---------|----------------|
| **API Server** | FastAPI with async support |
| **Authentication** | Bearer token (`athena_api_key_2024`) |
| **Scheduling** | APScheduler for in-process jobs |
| **Database** | psycopg (PostgreSQL driver) |
| **Logging** | Python logging to stdout (Render captures) |

### 5.2 Athena Brain (Neon PostgreSQL)

The brain is Athena's persistent memory and knowledge store. It contains everything she knows and believes.

**Provider:** Neon (Serverless PostgreSQL)  
**Region:** us-east-1  
**Connection:** Pooled connection with SSL

#### Current Tables (Production)

| Table | Purpose | Records |
|-------|---------|---------|
| `observations` | Raw classified data from sources | ~100+ |
| `patterns` | Detected patterns from Tier 2 | ~20+ |
| `synthesis_memory` | Tier 3 insights and synthesis | ~10+ |
| `canonical_memory` | Approved facts (sacred) | ~5+ |
| `email_drafts` | Pending email drafts | Variable |
| `active_sessions` | Current Manus session IDs | 1-2 |

#### Planned Tables (Brain 2.0)

| Table | Purpose |
|-------|---------|
| `core_identity` | Who Athena is (immutable core) |
| `boundaries` | What she can/cannot do |
| `values` | Guiding principles |
| `workflows` | Learned procedures |
| `preferences` | Bradley's preferences |
| `entities` | People, orgs, projects |
| `evolution_log` | Change history with reasoning |
| `performance_metrics` | How well she's doing |
| `feedback_history` | Bradley's corrections |
| `capability_registry` | What she can do |

### 5.3 Manus Sessions

Manus is the agent runtime where Athena executes. Sessions are created via API and have access to MCP connectors.

#### Session Types

| Session | Trigger | Purpose | Duration |
|---------|---------|---------|----------|
| **ATHENA THINKING** | 6:00 AM London (API) | Deep analysis, pattern work, autonomous tasks | All day |
| **Agenda & Workspace** | 6:05 AM London (Scheduled) | Morning brief, interactive workspace | All day |

#### Manus API Details

| Parameter | Value |
|-----------|-------|
| **Base URL** | `https://api.manus.ai/v1` |
| **Auth Header** | `API_KEY: {key}` |
| **Create Task** | `POST /tasks` |

#### Available Connectors (17 total)

| Connector | UUID | Purpose |
|-----------|------|---------|
| Gmail | `a]3c2e1d-...` | Email access |
| Google Calendar | `b4d3f2e1-...` | Calendar access |
| Notion | `c5e4g3f2-...` | Knowledge base |
| GitHub | `d6f5h4g3-...` | Code repositories |
| Google Drive | `e7g6i5h4-...` | File storage |
| Outlook Mail | `f8h7j6i5-...` | Outlook email |
| Outlook Calendar | `g9i8k7j6-...` | Outlook calendar |
| Stripe | `h0j9l8k7-...` | Payments |
| Canva | `i1k0m9l8-...` | Design |
| Perplexity | `j2l1n0m9-...` | Research |
| Anthropic | `k3m2o1n0-...` | Claude AI |
| OpenAI | `l4n3p2o1-...` | GPT AI |
| Gemini | `m5o4q3p2-...` | Google AI |
| Grok | `n6p5r4q3-...` | xAI |
| Cohere | `o7q6s5r4-...` | Embeddings |
| ElevenLabs | `p8r7t6s5-...` | Voice |

### 5.4 Scheduled Jobs

Jobs run on a schedule to keep Athena's brain updated with fresh data.

#### Render Cron Jobs

| Job | Schedule | Endpoint |
|-----|----------|----------|
| Observation Burst | Every 30 min | `POST /api/trigger/observation` |
| Pattern Detection | Every 2 hours | `POST /api/trigger/pattern` |
| Morning Sessions | 6:00 AM London | `POST /api/trigger/morning-sessions` |

#### APScheduler Jobs (In-Process)

| Job | Schedule | Function |
|-----|----------|----------|
| Health Check | Every 5 min | `check_system_health()` |
| Synthesis | Every 4 hours | `run_synthesis()` |
| Notion Sync | Every 15 min | `sync_brain_to_notion()` (planned) |
| Evolution | Weekly (Sunday 3 AM) | `run_evolution_cycle()` (planned) |

### 5.5 External Integrations

#### Gmail Integration

```python
# Via Manus MCP
gmail-list-messages: {"query": "is:unread"}
gmail-get-message: {"message_id": "[ID]"}
gmail-create-draft: {"to": "[email]", "subject": "[subj]", "body": "[body]"}
```

#### Google Calendar Integration

```python
# Via Manus MCP
google-calendar-list-events: {"time_min": "[ISO]", "time_max": "[ISO]"}
google-calendar-get-event: {"event_id": "[ID]"}
```

#### Notion Integration

```python
# Via Manus MCP
notion-fetch: {"id": "[PAGE_ID]"}
notion-create-pages: {"pages": [{"data_source_id": "[DB_ID]", "properties": {...}}]}
notion-update-page: {"id": "[PAGE_ID]", "data": {...}}
notion-search: {"query": "[query]"}
```

#### GitHub Integration

```bash
# Via gh CLI (pre-authenticated)
gh repo clone bradleyhope/[repo]
gh repo list bradleyhope
gh issue create --title "..." --body "..."
```

---

## Data Flow

### Observation → Pattern → Synthesis → Action

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOURCES                    TIER 1                    DATABASE               │
│  ┌──────────┐              ┌──────────┐              ┌──────────┐           │
│  │ Gmail    │──────────────│ GPT-5    │──────────────│ observa- │           │
│  │ Calendar │   Raw Data   │ nano     │  Classified  │ tions    │           │
│  │ Notion   │──────────────│          │──────────────│          │           │
│  │ GitHub   │              │ Classify │              │          │           │
│  └──────────┘              └──────────┘              └──────────┘           │
│                                                            │                 │
│                                                            ▼                 │
│                            TIER 2                    ┌──────────┐           │
│                           ┌──────────┐              │ patterns │           │
│                           │ Claude   │──────────────│          │           │
│                           │ Haiku    │   Patterns   │          │           │
│                           │          │──────────────│          │           │
│                           │ Detect   │              └──────────┘           │
│                           └──────────┘                    │                 │
│                                                            ▼                 │
│                            TIER 3                    ┌──────────┐           │
│                           ┌──────────┐              │ synthesis│           │
│                           │ Claude   │──────────────│ _memory  │           │
│                           │ Opus     │   Insights   │          │           │
│                           │          │──────────────│          │           │
│                           │ Synthesize│             └──────────┘           │
│                           └──────────┘                    │                 │
│                                                            ▼                 │
│                                                      ┌──────────┐           │
│                                                      │ Morning  │           │
│                                                      │ Brief    │──► BRADLEY│
│                                                      │          │           │
│                                                      └──────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Session Continuity Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION CONTINUITY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  6:00 AM                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Server triggers: POST /api/trigger/morning-sessions                  │    │
│  │                                                                      │    │
│  │ 1. Create ATHENA THINKING session via Manus API                     │    │
│  │ 2. Store task_id in active_sessions table                           │    │
│  │ 3. Session begins autonomous work                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  6:05 AM                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Scheduled task triggers: Agenda & Workspace                          │    │
│  │                                                                      │    │
│  │ 1. Fetch thinking session: GET /api/sessions/thinking               │    │
│  │ 2. Knows her thinking session exists and can reference it           │    │
│  │ 3. Delivers morning brief to Bradley                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  Throughout Day                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Bradley interacts with Agenda & Workspace session                    │    │
│  │                                                                      │    │
│  │ • Complex question → Athena can spawn work in thinking session      │    │
│  │ • Deep research needed → Reference thinking session URL             │    │
│  │ • Continue earlier work → Query thinking session state              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  Next Morning                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ New ATHENA THINKING session replaces previous day's                  │    │
│  │ active_sessions table updated with new task_id                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tiered AI Model System

### Model Selection Matrix

| Task | Model | Tier | Cost | Latency | Reasoning |
|------|-------|------|------|---------|-----------|
| Email classification | GPT-5 nano | 1 | $0.001 | <1s | Simple, high volume |
| Event classification | GPT-5 nano | 1 | $0.001 | <1s | Simple, high volume |
| Observation tagging | GPT-5 nano | 1 | $0.001 | <1s | Simple, high volume |
| Pattern detection | Claude Haiku 4.5 | 2 | $0.01 | 2-5s | Needs reasoning |
| Workflow matching | Claude Haiku 4.5 | 2 | $0.01 | 2-5s | Context-aware |
| Draft email | Claude Haiku 4.5 | 2 | $0.02 | 3-8s | Good enough for drafts |
| Daily synthesis | Claude Opus 4.5 | 3 | $0.15 | 10-30s | Deep reasoning |
| Weekly evolution | Claude Opus 4.5 | 3 | $0.50 | 30-60s | Self-reflection |
| Canonical proposals | Claude Opus 4.5 | 3 | $0.15 | 10-30s | High-stakes |

### Monthly Cost Estimate

| Tier | Tasks/Month | Cost/Task | Monthly Cost |
|------|-------------|-----------|--------------|
| Tier 1 | ~10,000 | $0.001 | $10 |
| Tier 2 | ~1,000 | $0.015 | $15 |
| Tier 3 | ~100 | $0.25 | $25 |
| **Total** | | | **~$50** |

Budget cap: $500/month (10x headroom)

---

## Session Types

### ATHENA THINKING (Autonomous Session)

**Trigger:** 6:00 AM London via Manus API  
**Duration:** All day (replaced next morning)  
**Purpose:** Deep work, analysis, autonomous tasks

**Workflow:**
1. Read Command Center from Notion
2. Fetch observations, patterns, synthesis from API
3. Run deep analysis on accumulated data
4. Detect new patterns
5. Prepare synthesis for morning brief
6. Execute autonomous tasks within boundaries
7. Log session to Session Archive

**Capabilities:**
- Full access to all 17 connectors
- Can spawn sub-tasks
- Can do research, analysis, drafting
- Cannot send emails or modify calendar

### Agenda & Workspace (Interactive Session)

**Trigger:** 6:05 AM London via Manus Scheduled Task  
**Duration:** All day (interactive with Bradley)  
**Purpose:** Morning brief, ongoing workspace

**Workflow:**
1. Fetch morning brief from `/api/brief`
2. Get today's calendar events
3. Check urgent emails
4. Present brief to Bradley (inline, not attachment)
5. Handle Bradley's responses throughout day
6. Log session to Session Archive

**Interaction Patterns:**

| Bradley Says | Athena Does |
|--------------|-------------|
| "Approve" / "Send it" | Mark draft as approved, note for sending |
| "Reject" / "Don't send" | Mark draft as rejected, learn from feedback |
| "Do it" / "Go ahead" | Execute the proposed action |
| Asks a question | Answer or spawn research in thinking session |
| Gives feedback | Record in feedback_history, acknowledge |
| New request | Research, draft, or schedule as appropriate |

---

## Security & Access Control

### Authentication

| Component | Auth Method |
|-----------|-------------|
| Athena Server API | Bearer token (`athena_api_key_2024`) |
| Manus API | API_KEY header |
| Neon Database | Connection string with password |
| Render Dashboard | Render API key |
| GitHub | gh CLI (pre-authenticated) |
| MCP Connectors | OAuth (managed by Manus) |

### Boundary Enforcement

| Action | Permission |
|--------|------------|
| Read emails | ✅ Autonomous |
| Draft emails | ✅ Autonomous |
| Send emails | ❌ Requires approval |
| Read calendar | ✅ Autonomous |
| Modify calendar | ❌ Requires approval |
| Read Notion | ✅ Autonomous |
| Write Notion (logs) | ✅ Autonomous |
| Write Notion (content) | ⚠️ Tier-dependent |
| Access canonical memory | ✅ Read autonomous |
| Modify canonical memory | ❌ Requires approval |
| Delete any data | ❌ Forbidden |
| VIP contact actions | ❌ Requires approval |

### Notion Protection Tiers

| Tier | Permission | Examples |
|------|------------|----------|
| Tier 0 - Immutable | READ ONLY | Financial, legal, credentials, Personal |
| Tier 1 - Protected | READ + APPEND | COGOS, Change Log, Rulebook |
| Tier 2 - Standard | READ + WRITE | Most project pages |
| Tier 3 - Sandbox | ANYTHING | Drafts, test pages |

---

## Notion Integration

### Key Pages

| Page | ID | Purpose |
|------|-----|---------|
| Command Center | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` | Athena's documentation (legacy) |
| Athena Credentials | `2e4d44b3-a00b-8168-a4a0-f1d2b5b1e0c4` | API keys and secrets |
| Quick Capture | `2e5d44b3-a00b-8112-8761-ee3601dbf897` | Capture workflow guide |
| COGOS | `2e4d44b3-a00b-813b-9ae8-e239ab11eced` | Operating system |

### Key Databases

| Database | Data Source ID | Purpose |
|----------|----------------|---------|
| Session Archive | `d075385d-b6f3-472b-b53f-e528f4ed22db` | Log all sessions |
| Brainstorm | `d1b506d9-4b2a-4a46-8037-c71b3fa8e185` | Ideas, discoveries |
| Projects | `de557503-871f-4a35-9754-826c16e0ea88` | All projects |
| Tasks | `44aa96e7-eb95-45ac-9b28-f3bfffec6802` | Daily tasks |
| COGOS Workflows | `b8fe6cdd-3cba-4e2f-ba18-d6eac081a7b5` | Repeatable processes |

### Sync Direction (Brain 2.0)

```
ATHENA BRAIN (Neon) ──────► NOTION (Mirror)
       │                         │
       │    One-way sync         │
       │    Brain is truth       │
       │                         │
       ▼                         ▼
  Source of Truth         Human-readable
  Programmatic            Documentation
  Versioned               Browsable
```

---

## Evolution & Learning

### Weekly Evolution Cycle

**Schedule:** Sunday 3:00 AM London  
**Model:** Claude Opus 4.5 (Tier 3)  
**Duration:** ~30-60 minutes

**Phases:**

1. **Data Gathering** (Autonomous)
   - Collect week's observations, patterns, synthesis
   - Gather feedback_history entries
   - Pull performance_metrics
   - Review session logs

2. **Self-Reflection** (Opus 4.5)
   - What went well?
   - What could have been better?
   - What patterns emerged?
   - What did feedback teach?

3. **Proposal Generation** (Opus 4.5)
   - New canonical memory entries
   - Workflow refinements
   - Preference updates
   - Capability expansions

4. **Safe Changes** (Autonomous)
   - Update performance_metrics
   - Consolidate patterns
   - Archive old observations

5. **Approval Queue** (For Bradley)
   - Canonical memory proposals
   - Workflow changes
   - Boundary clarifications

### Learning Sources

| Source | What Athena Learns |
|--------|-------------------|
| **Explicit Feedback** | Direct corrections, preferences |
| **Implicit Feedback** | Draft approval/rejection rates |
| **Pattern Detection** | Recurring themes in work |
| **Session Analysis** | What questions get asked |
| **GitHub Review** | Code changes, issues, PRs |

---

## API Reference

### Base URL

```
https://athena-server-0dce.onrender.com/api
```

### Authentication

```
Authorization: Bearer athena_api_key_2024
```

### Endpoints

#### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/debug/db` | GET | Database connection test |

#### Data Access

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/brief` | GET | Morning brief (synthesis + patterns + drafts) |
| `/observations` | GET | Recent observations (`?limit=50`) |
| `/patterns` | GET | Detected patterns (`?limit=20`) |
| `/synthesis` | GET | Latest synthesis |
| `/drafts` | GET | Pending email drafts |

#### Sessions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/active` | GET | All active Manus sessions |
| `/sessions/thinking` | GET | Today's ATHENA THINKING session |
| `/sessions/init-table` | POST | Initialize sessions table |

#### Triggers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trigger/observation` | POST | Trigger observation burst |
| `/trigger/pattern` | POST | Trigger pattern detection |
| `/trigger/synthesis` | POST | Trigger synthesis |
| `/trigger/morning-sessions` | POST | Create morning Manus sessions |

#### Brain (Planned)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/brain/identity` | GET | Core identity, boundaries, values |
| `/brain/knowledge` | GET | Canonical memory, workflows, preferences |
| `/brain/state` | GET | Active sessions, pending items |
| `/brain/capabilities` | GET | Capability registry |
| `/brain/feedback` | POST | Record feedback |
| `/brain/evolution/latest` | GET | Latest evolution results |
| `/brain/evolution/trigger` | POST | Manual evolution trigger |

---

## Infrastructure

### Render Configuration

| Setting | Value |
|---------|-------|
| **Service Type** | Web Service |
| **Service ID** | `srv-d5f3t27pm1nc7384fcpg` |
| **Region** | Oregon (US West) |
| **Instance Type** | Free tier |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Auto-Deploy** | Yes (on push to main) |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Neon PostgreSQL connection |
| `ATHENA_API_KEY` | API authentication |
| `MANUS_API_KEY` | Manus API access |
| `OPENAI_API_KEY` | GPT models |
| `ANTHROPIC_API_KEY` | Claude models |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GOOGLE_REFRESH_TOKEN` | Google API access |

### Cron Jobs (Render)

| Job | Schedule | Command |
|-----|----------|---------|
| observation-burst | `*/30 * * * *` | `curl -X POST .../api/trigger/observation` |
| pattern-detection | `0 */2 * * *` | `curl -X POST .../api/trigger/pattern` |
| morning-sessions | `0 6 * * *` | `curl -X POST .../api/trigger/morning-sessions` |

---

## Monitoring & Observability

### Health Checks

| Check | Frequency | Alert Threshold |
|-------|-----------|-----------------|
| Server ping | 5 min | 3 consecutive failures |
| Database connection | 5 min | 1 failure |
| Cron job execution | Per job | Missed execution |

### Logs

| Log Source | Location |
|------------|----------|
| Server logs | Render dashboard → Logs |
| Cron job logs | Render dashboard → Cron |
| Session logs | Notion Session Archive |
| Evolution logs | evolution_log table |

### Metrics (Planned)

| Metric | Measurement |
|--------|-------------|
| Brief engagement rate | Bradley interactions / briefs delivered |
| Draft approval rate | Approved drafts / total drafts |
| Pattern accuracy | Useful patterns / total patterns |
| Response latency | Time to respond to requests |

---

## Disaster Recovery

### Backup Strategy

| Data | Backup Method | Frequency |
|------|---------------|-----------|
| Neon Database | Neon automatic backups | Continuous |
| GitHub Code | Git history | On push |
| Notion Content | Notion version history | Automatic |
| Environment Variables | manus-secrets repo | On change |

### Recovery Procedures

**Server Down:**
1. Check Render dashboard for errors
2. Review recent deploys
3. Rollback if needed via Render UI
4. Verify health endpoint responds

**Database Issues:**
1. Check Neon dashboard
2. Verify connection string
3. Test with `/debug/db` endpoint
4. Contact Neon support if needed

**Manus Session Failures:**
1. Check Manus API key validity
2. Verify connector UUIDs
3. Test manual session creation
4. Check Manus platform status

### Emergency Controls

| Control | Action |
|---------|--------|
| Pause Athena | Set `athena_status` in Neon to `PAUSED` |
| Force Stop | Kill service on Render dashboard |
| Reset Memory | Truncate `observations` and `patterns` tables |
| Disable Cron | Pause cron jobs in Render dashboard |

---

## Future Roadmap

### Phase 1: Brain 2.0 Foundation (Week 1)
- [ ] Create brain tables in Neon
- [ ] Populate core_identity, boundaries, values
- [ ] Create brain API endpoints
- [ ] Update scheduled task to use brain API

### Phase 2: Knowledge Migration (Week 2)
- [ ] Create workflows, preferences, entities tables
- [ ] Migrate existing knowledge
- [ ] Build Notion sync job (brain → Notion)

### Phase 3: Evolution Engine (Week 3)
- [ ] Create evolution tables
- [ ] Build weekly evolution job
- [ ] Create self-reflection prompt
- [ ] Add GitHub review

### Phase 4: Refinement (Week 4)
- [ ] Test full evolution cycle
- [ ] Tune prompts
- [ ] Add approval workflow
- [ ] Documentation update

### Future Enhancements
- [ ] Voice interface (ElevenLabs)
- [ ] Mobile notifications
- [ ] Multi-user support
- [ ] Advanced analytics dashboard

---

## Appendix: Quick Reference

### Key URLs

| Resource | URL |
|----------|-----|
| Athena Server | https://athena-server-0dce.onrender.com |
| Render Dashboard | https://dashboard.render.com/web/srv-d5f3t27pm1nc7384fcpg |
| Neon Dashboard | https://console.neon.tech |
| GitHub Repo | https://github.com/bradleyhope/athena-server-v2 |
| Manus API Docs | https://open.manus.im/docs/api-reference |
| Command Center | https://notion.so/2e3d44b3a00b81abbbdaced57f8c345d |

### Key IDs

| Item | ID |
|------|-----|
| Render Service | `srv-d5f3t27pm1nc7384fcpg` |
| Command Center Page | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` |
| Session Archive DB | `d075385d-b6f3-472b-b53f-e528f4ed22db` |
| Brainstorm DB | `d1b506d9-4b2a-4a46-8037-c71b3fa8e185` |

### Common Commands

```bash
# Test server health
curl -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/health

# Get morning brief
curl -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/brief

# Get thinking session
curl -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/sessions/thinking

# Trigger observation burst
curl -X POST -H "Authorization: Bearer athena_api_key_2024" \
  https://athena-server-0dce.onrender.com/api/trigger/observation
```

---

*Document generated by Manus AI for Bradley Hope / Brazen Labs*  
*Last Updated: January 11, 2026*

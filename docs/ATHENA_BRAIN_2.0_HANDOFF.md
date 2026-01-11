# Athena Brain 2.0 Upgrade — Session Handoff

**Date:** January 11, 2026  
**Session Type:** Athena Architecture (Long-running)  
**Purpose:** Implement Brain 2.0 - Transform Athena from Notion-dependent to truly intelligent

---

## INITIALIZATION REQUIREMENTS

Before starting ANY work, you MUST:

### 1. Read the Architecture Initialization Page
```
notion-fetch: 2e5d44b3-a00b-816e-9168-f7c167f1e69e
```

### 2. Clone and Review the Athena Server
```bash
gh repo clone bradleyhope/athena-server-v2
```
Key files to read:
- `main.py` - FastAPI app entry point
- `config.py` - Environment configuration
- `api/routes.py` - All API endpoints
- `db/neon.py` - Database operations
- `jobs/` - All scheduled jobs

### 3. Read COMPASS Principles
```
notion-fetch: 2e3d44b3-a00b-814e-83a6-c30e751d6042
```

### 4. Read FORGE Tools
```
notion-fetch: 2e3d44b3-a00b-81cc-99c7-cf0892cbeceb
```

### 5. Read Canonical Guide to AI
```
notion-fetch: 2dfd44b3-a00b-81d7-855f-d4fcc01a709f
```

### 6. Log This Session
Create entry in Session Archive (data_source_id: d075385d-b6f3-472b-b53f-e528f4ed22db):
- Title: "Athena Architecture - Brain 2.0 Upgrade - [Date]"
- Agent: "ARCHITECTURE"
- Session Type: "Athena Architecture"

---

## CREDENTIALS (All Required)

### Neon PostgreSQL Database
```
Host: ep-rough-paper-a4zrxoej-pooler.us-east-1.aws.neon.tech
Database: neondb
User: neondb_owner
Password: npg_tk0Re2adLnbM
SSL: Required

Connection String:
postgresql://neondb_owner:npg_tk0Re2adLnbM@ep-rough-paper-a4zrxoej-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Render API
```
API Key: rnd_Tiw53y9DGLwHQD2BxOFah4NyANvm
Service ID: srv-d5f3t27pm1nc7384fcpg
Dashboard: https://dashboard.render.com/web/srv-d5f3t27pm1nc7384fcpg
```

### Manus API
```
Base URL: https://api.manus.ai/v1
Auth Header: API_KEY (NOT Bearer)
API Key: sk-rNTzbonQ9Y0pfVhTicKo6POXtCqfkfM_JhMlmZldLmYv8nyRrj9bINqKl0vs8nnvkuSpJ4unOGA2v4-O
```

### Athena Server API
```
Base URL: https://athena-server-0dce.onrender.com/api
Auth Header: Authorization: Bearer athena_api_key_2024
```

---

## CURRENT SYSTEM STATE

### What Exists (Production)

**Server:** FastAPI on Render (live)
- Health: https://athena-server-0dce.onrender.com/api/health
- All endpoints working

**Database Tables (Neon):**
- `observations` - Raw classified data
- `patterns` - Detected patterns
- `synthesis_memory` - Tier 3 insights
- `canonical_memory` - Approved facts
- `email_drafts` - Pending drafts
- `active_sessions` - Current Manus session IDs

**Cron Jobs (Render):**
- `athena-observation-burst` - Every 30 min
- `athena-pattern-detection` - Every 2 hours
- `athena-morning-sessions` - 5:30 AM London (creates ATHENA THINKING session)

**Scheduled Task (Manus):**
- "Agenda & Workspace" - 6:05 AM London

### What's Missing (Brain 2.0)

The current system reads instructions from Notion. Brain 2.0 changes this:

**Brain = Source of Truth** (not Notion)
**Notion = Human-readable mirror** (one-way sync from brain)

New tables needed:
- `core_identity` - Who Athena is
- `boundaries` - What she can/cannot do
- `values` - Guiding principles
- `workflows` - Learned procedures
- `preferences` - Bradley's preferences
- `entities` - People, orgs, projects
- `evolution_log` - Change history
- `performance_metrics` - How well she's doing
- `feedback_history` - Bradley's corrections
- `capability_registry` - What she can do

---

## THE BRAIN 2.0 ARCHITECTURE

### Core Principle

```
WRONG (Current):
Notion (source of truth) → Athena reads → Takes action

CORRECT (Brain 2.0):
Athena Brain (Neon DB) = Source of Truth
     ↓
Athena acts based on her own knowledge
     ↓
Notion = Human-readable mirror of her state
```

### Tiered AI Model System

| Task | Model | Tier |
|------|-------|------|
| Email classification | GPT-5 nano | 1 |
| Pattern detection | Claude Haiku 4.5 | 2 |
| Daily synthesis | Claude Opus 4.5 | 3 |
| **Weekly evolution** | **Claude Opus 4.5** | **3** |

### Evolution Engine (Weekly, Opus 4.5)

The self-improvement process uses the HIGHEST tier AI:

1. **Data Gathering** (autonomous)
2. **Self-Reflection** (Opus 4.5) - What worked, what didn't
3. **Proposal Generation** (Opus 4.5) - Canonical memory, workflows
4. **Safe Changes** (autonomous) - Metrics, consolidation
5. **Approval Queue** (for Bradley) - Critical changes

---

## THREE SESSION ARCHITECTURE

| Session | Time (London) | Purpose |
|---------|---------------|---------|
| ATHENA THINKING | 5:30 AM | Athena's autonomous work |
| Agenda & Workspace | 6:05 AM | Bradley's interactive workspace |
| **Athena Architecture** | **Manual** | **Big-picture system work (this session)** |

---

## KEY NOTION PAGES

| Page | ID |
|------|-----|
| Command Center | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` |
| COGOS | `2e4d44b3-a00b-813b-9ae8-e239ab11eced` |
| Compass | `2e3d44b3-a00b-814e-83a6-c30e751d6042` |
| Forge | `2e3d44b3-a00b-81cc-99c7-cf0892cbeceb` |
| Credentials | `2e2d44b3-a00b-81d1-b1b9-fb2bfd3596aa` |
| Architecture Init | `2e5d44b3-a00b-816e-9168-f7c167f1e69e` |
| Session Archive DB | `d075385d-b6f3-472b-b53f-e528f4ed22db` |

---

## KEY GITHUB REPOS

| Repo | Purpose |
|------|---------|
| bradleyhope/athena-server-v2 | Athena server code |
| bradleyhope/forge | Multi-agent AI engineering |
| bradleyhope/vibe-coding-starter | COMPASS framework |
| bradleyhope/manus-secrets | Credentials (private) |

---

## IMPLEMENTATION ROADMAP

### Week 1: Foundation
- [ ] Create brain tables in Neon
- [ ] Populate core_identity, boundaries, values
- [ ] Create brain API endpoints
- [ ] Update scheduled task to use brain API

### Week 2: Knowledge Migration
- [ ] Create workflows, preferences, entities tables
- [ ] Migrate existing knowledge
- [ ] Build Notion sync job (brain → Notion)

### Week 3: Evolution Engine
- [ ] Create evolution tables
- [ ] Build weekly evolution job
- [ ] Create self-reflection prompt for Opus 4.5
- [ ] Add GitHub review capability

### Week 4: Refinement
- [ ] Test full evolution cycle
- [ ] Tune prompts
- [ ] Add approval workflow
- [ ] Documentation update

---

## FIRST STEPS FOR THIS SESSION

1. **Read everything** listed in INITIALIZATION REQUIREMENTS
2. **Give general thoughts** on the system architecture
3. **Log this session** to Session Archive
4. **Propose implementation plan** based on Brain 2.0 architecture
5. **Start with Week 1** - Create brain tables

---

## REFERENCE DOCUMENTS

Full architecture documents are available at:
- `/home/ubuntu/ATHENA_2.0_COMPLETE_ARCHITECTURE.md`
- `/home/ubuntu/ATHENA_BRAIN_2.0_ARCHITECTURE.md`

These contain complete SQL schemas, API designs, and implementation details.

---

## SESSION RULES

1. **You are working ON Athena, not AS Athena** - This is meta-level work
2. **Bradley is the architect** - You assist, he decides
3. **Understand before changing** - Read architecture first
4. **Small changes** - Iterative development, not big-bang
5. **Document everything** - Future sessions need context
6. **Respect active sessions** - Don't break running systems
7. **Use COMPASS** - Plan before you code
8. **Consider FORGE** - Use specialized agents when appropriate

---

*Handoff prepared by Manus AI on January 11, 2026*

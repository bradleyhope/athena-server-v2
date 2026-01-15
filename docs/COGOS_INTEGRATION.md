# ATHENA ↔ COGOS Integration

**Version:** 1.0 | **Updated:** 2026-01-15

---

## Overview

ATHENA is a **COGOS subsystem** — it inherits core COGOS principles and extends them for persistent autonomous agent functionality.

This document describes how ATHENA integrates with the broader COGOS ecosystem.

---

## Cross-Links

### COGOS System

| Resource | Location | Purpose |
|----------|----------|---------|
| **COGOS.md** | `cogos-system/COGOS.md` | Master COGOS documentation (see Subsystems section) |
| **Project YAML** | `cogos-system/projects/labs/athena.yaml` | Comprehensive project definition (535 lines) |
| **Session Types** | `cogos-system/docs/athena/SESSION_TYPES.md` | Session type guide |
| **Workspace Workflow** | `cogos-system/workflows-structured/athena-workspace.yaml` | Daily work workflow |
| **Thinking Workflow** | `cogos-system/workflows-structured/athena-thinking.yaml` | System improvement workflow |
| **Email Workflow** | `cogos-system/preferences/athena-email-workflow.md` | Email rules |
| **Tool Doc** | `cogos-system/tools/ATHENA.md` | Quick reference |

### GitHub Repositories

| Repository | Purpose |
|------------|---------|
| [bradleyhope/athena-server-v2](https://github.com/bradleyhope/athena-server-v2) | This repo — FastAPI backend |
| [bradleyhope/cogos-system](https://github.com/bradleyhope/cogos-system) | COGOS project definitions, workflows |

### Notion Pages

| Page | ID | Purpose |
|------|-----|---------|
| Athena Command Center | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` | Master reference |
| Athena Canonical Memory | `2e4d44b3-a00b-810e-9ac1-cbd30e209fab` | Approved facts |
| Athena VIP Contacts | `2e4d44b3-a00b-8112-8eb2-ef28cec19ae6` | High-stakes contacts |
| Athena Policies & Rules | `2e4d44b3-a00b-813c-a564-c7950f0db4a5` | Behavioral rules |

---

## Session Types

ATHENA operates through distinct session types, each with a specific purpose:

| Session | Init Command | Purpose | Mode |
|---------|--------------|---------|------|
| **Workspace** | `init athena` | Daily work | Working IN Athena |
| **Thinking** | `init athena-thinking` | System improvement | Working ON Athena |
| **Architecture** | `init athena-architecture` | Code changes | Working ON Athena |

See `cogos-system/docs/athena/SESSION_TYPES.md` for full details.

---

## COGOS Principles Applied

ATHENA inherits these core COGOS principles:

### 1. GitHub as Source of Truth
- Server code lives in this repo
- Project definition lives in `cogos-system/projects/labs/athena.yaml`
- Notion is a view layer, not source of truth

### 2. Sandbox Lifecycle Awareness
- Manus sandboxes recycle after 7-21 days of inactivity
- Always clone repos fresh at session start
- Don't assume local state persists

### 3. Session Logging
- All sessions logged to Session Archive with `agent: "ATHENA"`
- Captures workflows used, friction points, learnings

### 4. Learning Loops
- Every session can improve the system
- Capture new workflows to COGOS Workflows DB
- Log insights to Brainstorm DB

---

## API Endpoints for COGOS Integration

### Session Initialization

```bash
# Initialize workspace session
GET /api/session/init/agenda_workspace

# Initialize thinking session
GET /api/session/init/athena_thinking

# Initialize general session
GET /api/session/init/general
```

These endpoints return session-specific context and system prompts.

### Brain Access

```bash
# Get pending evolution proposals
GET /api/brain/evolution/pending

# Get performance metrics
GET /api/brain/metrics

# Get pending actions
GET /api/brain/actions/pending
```

---

## Manus Knowledge Item

The ATHENA Manus Knowledge item should include:

```
ATHENA - Cognitive Extension System (COGOS Subsystem)

ATHENA is Bradley's persistent autonomous agent.

INITIALIZATION:
- "init athena" → Workspace session (emails, tasks, calendar)
- "init athena-thinking" → Thinking session (improve Athena)
- "init athena-architecture" → Architecture session (code changes)

BOOTSTRAP:
1. Clone: gh repo clone bradleyhope/cogos-system
2. Read: /home/ubuntu/cogos-system/projects/labs/athena.yaml
3. Call Brain API: GET https://athena-server-0dce.onrender.com/api/session/init/{type}

KEY RESOURCES:
- Server: https://athena-server-0dce.onrender.com
- Command Center: Notion 2e3d44b3-a00b-81ab-bbda-ced57f8c345d
- Tasks DB: 44aa96e7-eb95-45ac-9b28-f3bfffec6802

RULES:
- Follow email workflow (never send without approval)
- Log sessions with agent: "ATHENA"
- Neon PostgreSQL is source of truth, Notion is view layer
```

---

## Related Documentation

- [README.md](../README.md) — Server overview
- [CLAUDE_REPOSITORY_GUIDE.md](../CLAUDE_REPOSITORY_GUIDE.md) — Repository structure
- [CLAUDE_SCHEMA_DOCUMENTATION.md](../CLAUDE_SCHEMA_DOCUMENTATION.md) — Database schema

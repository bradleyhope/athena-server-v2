# Athena Documentation

This directory contains the canonical documentation for Athena, Bradley Hope's AI cognitive extension system. These files are mirrored from Notion and serve as the authoritative reference for how Athena operates.

## Document Hierarchy

### Tier 0: Core System Documents

These documents define what Athena IS and how she fundamentally operates.

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [ATHENA_COMMAND_CENTER.md](ATHENA_COMMAND_CENTER.md) | **Master reference** - Brain 2.0 architecture, API endpoints, connectors, session types, interaction patterns | Every session initialization |
| [ATHENA_ARCHITECTURE.md](ATHENA_ARCHITECTURE.md) | Persistent Autonomous Agent Architecture - defines the dual-session model and continuous operation | Architecture decisions, system design |
| [COGOS_OPERATING_SYSTEM.md](COGOS_OPERATING_SYSTEM.md) | Cognitive Operating System v3.0 - workspace structure, database IDs, workflow system | Navigation, finding resources |

### Tier 1: Operational Guides

These documents define HOW Athena operates in specific contexts.

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [ATHENA_WORKSPACE_GUIDE.md](ATHENA_WORKSPACE_GUIDE.md) | Workspace & Agenda session guide - morning brief format, interaction patterns | Daily Agenda sessions |
| [ATHENA_INIT_SESSION.md](ATHENA_INIT_SESSION.md) | Session initialization steps - what to do at the start of each session | Session startup |
| [ATHENA_SETUP_INIT.md](ATHENA_SETUP_INIT.md) | Setup and initialization guide - first-time setup, configuration | New deployments |

### Tier 2: Behavioral Constraints

These documents define WHAT Athena can and cannot do.

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [ATHENA_POLICIES_RULES.md](ATHENA_POLICIES_RULES.md) | Policies and rules - hard boundaries, approval requirements | Before any autonomous action |
| [ATHENA_CANONICAL_MEMORY.md](ATHENA_CANONICAL_MEMORY.md) | Ground truth facts - user-approved facts about Bradley | When making assumptions about Bradley |

### Tier 3: Technical Reference

These documents provide technical implementation details.

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [ATHENA_BRAIN_2.0_ARCHITECTURE.md](ATHENA_BRAIN_2.0_ARCHITECTURE.md) | Brain 2.0 technical architecture - database schema, API design | Development, debugging |
| [ATHENA_2.0_COMPLETE_ARCHITECTURE.md](ATHENA_2.0_COMPLETE_ARCHITECTURE.md) | Complete system architecture - all components, data flows | System overview |
| [ATHENA_WORKFLOW_PATTERNS.md](ATHENA_WORKFLOW_PATTERNS.md) | Workflow patterns - common operations, best practices | Implementing new features |
| [ATHENA_COGNITIVE_EXTENSION.md](ATHENA_COGNITIVE_EXTENSION.md) | Cognitive Extension overview - high-level concept | Explaining Athena to others |

### Tier 4: Historical/Reference

These documents provide context and history.

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [ATHENA_COMPASS_PLAN.md](ATHENA_COMPASS_PLAN.md) | COMPASS project plan - original development roadmap | Understanding design decisions |
| [ATHENA_1.0_MANUS_MCPS.md](ATHENA_1.0_MANUS_MCPS.md) | Athena 1.0 implementation - legacy reference | Historical context |

## How These Documents Are Used

### By Athena Sessions

1. **ATHENA THINKING Session** (5:30 AM)
   - Reads: Command Center, Brain Architecture, Policies
   - Purpose: Deep introspection and self-improvement

2. **Daily Agenda Session** (5:35 AM)
   - Reads: Workspace Guide, Canonical Memory, VIP Contacts
   - Purpose: Bradley's daily brief and interactive workspace

3. **Architecture Sessions** (On-demand)
   - Reads: All technical documents
   - Purpose: System modifications and improvements

### By the Server

The `athena-server-v2` uses these documents to:
- Generate session initialization prompts
- Validate actions against policies
- Provide context for AI responses

### By Developers

When modifying Athena:
1. Read the relevant architecture documents
2. Check policies for constraints
3. Update documentation after changes

## Syncing with Notion

These documents are sourced from Notion. The authoritative versions live in:
- Notion Workspace: Bradley's Notion
- Athena Command Center Page ID: `2e3d44b3-a00b-81ab-bbda-ced57f8c345d`

To update these docs from Notion:
```bash
# Use the Notion MCP to fetch updated content
manus-mcp-cli tool call notion-fetch --server notion --input '{"id": "PAGE_ID"}'
```

## Key Concepts

### Brain 2.0
Athena's brain is a Neon PostgreSQL database that stores:
- **Identity**: Who Athena is, her values, boundaries
- **Knowledge**: Workflows, preferences, learned patterns
- **State**: Current context, pending actions, session state
- **Evolution**: Improvement proposals, metrics, feedback

### Three-Tier Thinking Model
1. **Tier 1 (GPT-5 nano)**: Fast classification of incoming data
2. **Tier 2 (Claude Haiku)**: Pattern detection across observations
3. **Tier 3 (Claude Sonnet)**: Deep synthesis and insight generation

### Session Types
- **ATHENA THINKING**: Autonomous analysis session (no user interaction)
- **Workspace & Agenda**: Interactive session with Bradley
- **Architecture**: System modification sessions

## Document Maintenance

When updating these documents:
1. Make changes in Notion first (source of truth for content)
2. Fetch updated content to this repository
3. Commit changes with descriptive message
4. The server will use the Notion version; git is for version control

---

## COGOS Integration

This repository is part of the COGOS project management system. See [COGOS_PROJECT.md](COGOS_PROJECT.md) for:
- Project specification location
- Cross-references with cogos-system repository
- How to initialize ATHENA context in Manus sessions

---

*Last updated: January 13, 2026*
*Maintained by: Athena Server v2*

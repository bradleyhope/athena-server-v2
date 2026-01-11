# Athena Server v2 - Brain 2.0

This is the backend server for Athena 2.0, a cognitive extension system built on a four-layer brain architecture. The server is a FastAPI application that provides a three-tier thinking model, a comprehensive Brain API, and a series of scheduled jobs for continuous learning and system maintenance.

## Brain 2.0 Architecture

The core of Athena 2.0 is its brain, a Neon PostgreSQL database that serves as the single source of truth. This architecture transforms Athena from a Notion-dependent system into a truly intelligent agent with its own memory and reasoning capabilities. The brain is organized into four distinct layers:

### 1. Identity Layer

This layer defines Athena's core being and operational parameters.

- **`core_identity`**: Athena's name, role, version, and core personality traits.
- **`boundaries`**: Hard, soft, and contextual rules that govern Athena's behavior (e.g., "never send emails autonomously").
- **`values`**: Prioritized principles that guide decision-making in ambiguous situations (e.g., "User Sovereignty," "Proactive Assistance").

### 2. Knowledge Layer

This layer stores learned information and operational procedures.

- **`canonical_memory`**: User-approved facts about the world.
- **`workflows`**: Step-by-step procedures for accomplishing tasks (e.g., "morning_brief").
- **`preferences`**: Learned user preferences.
- **`entities`**: Information about people, places, and organizations.

### 3. State Layer

This layer manages the dynamic state of the system during operation.

- **`context_windows`**: Active context for ongoing conversations and tasks.
- **`pending_actions`**: Actions awaiting user approval or execution.
- **`session_state`**: Persistent state across Manus sessions.

### 4. Evolution Layer

This layer enables Athena to learn and improve over time.

- **`evolution_log`**: A record of all proposed and applied system changes.
- **`performance_metrics`**: Data on system performance and efficiency.
- **`feedback_history`**: A log of all user feedback for learning and adaptation.

## Brain API

The server exposes a comprehensive Brain API at `/api/brain/*` for interacting with all four layers of the brain. This API allows Manus sessions to read from and write to Athena's brain, enabling a tight integration between the agent and its memory.

Key endpoints include:

- `/api/brain/full-context`: Get the complete brain context for a Manus session.
- `/api/brain/identity`: Read and update Athena's core identity.
- `/api/brain/boundaries/check`: Check if an action is allowed by the defined boundaries.
- `/api/brain/workflows`: List and manage workflows.
- `/api/brain/actions`: Create and manage pending actions.
- `/api/brain/evolution`: Propose and manage system evolutions.

## Scheduled Jobs

The server runs a series of scheduled jobs to automate learning, synthesis, and maintenance:

- **Observation Burst** (every 30 mins): Gathers new information from various sources.
- **Pattern Detection** (every 2 hours): Identifies patterns in the collected observations.
- **Synthesis** (4x daily): Synthesizes new knowledge and proposes actions.
- **Morning Sessions** (6:00/6:05 AM London): Creates the "ATHENA THINKING" and "Agenda & Workspace" Notion pages.
- **Overnight Learning** (midnight-5am): Performs deep learning tasks.
- **Weekly Rebuild** (Sunday midnight): Rebuilds the synthesis memory.
- **Notion Sync** (every 4 hours): Mirrors the brain state to Notion for user visibility.

## Getting Started

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in the required values, especially `DATABASE_URL` and `ATHENA_API_KEY`.

### 2. Database Migration

To set up the Brain 2.0 schema, run the migration script:

```bash
python3 migrations/run_brain_2_0_migration.py
```

### 3. Running the Server

To run the server locally:

```bash
uvicorn main:app --reload
```

The server will be available at `http://localhost:3001`.

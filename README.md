# Athena Server v2

Cognitive Extension System for Bradley Hope - FastAPI server implementing the three-tier thinking model.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    athena-server (Brain)                                     │
│  • Tier 1/2/3 thinking loops                                                │
│  • Scheduled via APScheduler (burst every 15-30 min)                        │
│  • Direct AI model calls (OpenAI, Anthropic)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Neon PostgreSQL (Truth)                                   │
│  • Observations, patterns, synthesis_memory                                 │
│  • Canonical memory (approval-only)                                         │
│  • Email drafts, session state, emergency controls                          │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Manus Sessions (Hands)                                    │
│  • ATHENA THINKING [Date]: Athena's workspace                               │
│  • Agenda & Workspace - [Date]: Bradley's daily session                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Three-Tier Thinking Model

| Tier | Model | Frequency | Purpose |
|------|-------|-----------|---------|
| **Tier 1** | GPT-5 nano | Every 30 min | Classify observations |
| **Tier 2** | Claude Haiku 4.5 | Every 2 hours | Detect patterns |
| **Tier 3** | Claude Sonnet 4.5 | 4x daily | Deep synthesis |

## Scheduled Jobs

| Job | Schedule (London) | Description |
|-----|-------------------|-------------|
| Observation Burst | Every 30 min | Poll Gmail/Calendar, classify |
| Pattern Detection | Every 2 hours | Analyze observations |
| Synthesis | 6am, 12pm, 6pm, 10pm | Generate insights |
| ATHENA THINKING | 6:00 AM | Athena's workspace session |
| Agenda & Workspace | 6:05 AM | Bradley's morning brief |
| Overnight Learning | Midnight-5 AM | Read historical data |
| Weekly Rebuild | Sunday midnight | Fresh synthesis |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/health` | GET | Detailed health status |
| `/api/brief` | GET | Morning brief data |
| `/api/observations` | GET | Recent observations |
| `/api/patterns` | GET | Detected patterns |
| `/api/synthesis` | GET | Latest synthesis |
| `/api/drafts` | GET | Pending email drafts |
| `/api/trigger/observation` | POST | Manual observation burst |
| `/api/trigger/pattern` | POST | Manual pattern detection |
| `/api/trigger/synthesis` | POST | Manual synthesis |
| `/api/trigger/morning-sessions` | POST | Create morning sessions |

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in values
3. Install dependencies: `pip install -r requirements.txt`
4. Run locally: `uvicorn main:app --reload --port 3001`

## Deployment

Deploy to Render using the included `render.yaml`:

```bash
# Push to GitHub
git push origin main

# Render will auto-deploy from the render.yaml configuration
```

## Environment Variables

See `.env.example` for all required variables.

## Canonical Notion Pages

Athena reads these pages at session start:

| Page | ID |
|------|----|
| Athena Command Center | `2e3d44b3-a00b-81ab-bbda-ced57f8c345d` |
| Athena Canonical Memory | `2e4d44b3-a00b-810e-9ac1-cbd30e209fab` |
| Athena VIP Contacts | `2e4d44b3-a00b-8112-8eb2-ef28cec19ae6` |
| Athena Policies & Rules | `2e4d44b3-a00b-813c-a564-c7950f0db4a5` |

## AI Model IDs (January 2026)

| Model | API ID |
|-------|--------|
| GPT-5 nano | `gpt-5-nano` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| Manus 1.6 | `manus-1.6` |
| Manus 1.6 Lite | `manus-1.6-lite` |

<- Fixed observations endpoint to use source_type Deployment trigger: 20260111043602 -->
<- Fixed observations endpoint to use source_type Fixed DATABASE_URL: 20260111044522 -->

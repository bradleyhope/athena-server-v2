# Athena Brain 2.0: Architecture Proposal

**Author:** Manus AI  
**Date:** January 11, 2026  
**Version:** 1.0  
**Status:** Proposal for Review

---

## Executive Summary

This document proposes a fundamental architectural shift for Athena from a **Notion-dependent assistant** to a **truly intelligent cognitive system** with her own persistent brain. The core principle: **Athena's database is the source of truth; Notion is a human-readable reflection.**

The current architecture treats Notion as Athena's instruction manual—she reads it each session to know what to do. This is backwards. A cognitive extension should have internalized knowledge, learned behaviors, and the ability to evolve. Notion should mirror her state for human visibility, not define it.

---

## Part 1: The Problem with Current Architecture

### Current Flow (Flawed)

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Notion (Command Center)                                    │
│          │                                                   │
│          ▼                                                   │
│   Athena reads instructions ──► Takes action                 │
│          │                                                   │
│          ▼                                                   │
│   Logs back to Notion                                        │
│                                                              │
│   Problem: Athena is STATELESS between sessions              │
│   Problem: All knowledge lives in Notion (human-editable)    │
│   Problem: No learning, no evolution, no real intelligence   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Specific Issues

| Issue | Impact |
|-------|--------|
| **Stateless Sessions** | Each session starts fresh; no continuity of thought |
| **Notion as Source of Truth** | Human edits can break Athena; no programmatic control |
| **No Learning Loop** | Athena doesn't improve from experience |
| **No Self-Awareness** | Athena can't reflect on her own performance |
| **Scattered Knowledge** | Rules in Notion, data in Neon, no unified brain |

---

## Part 2: Athena Brain 2.0 Architecture

### New Flow (Correct)

```
┌─────────────────────────────────────────────────────────────┐
│                    ATHENA BRAIN 2.0                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              ATHENA'S BRAIN (Neon DB)                │   │
│   │                                                      │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │   │
│   │  │   IDENTITY   │  │  KNOWLEDGE   │  │   STATE   │  │   │
│   │  │              │  │              │  │           │  │   │
│   │  │ • Core rules │  │ • Canonical  │  │ • Active  │  │   │
│   │  │ • Boundaries │  │   memory     │  │   session │  │   │
│   │  │ • Purpose    │  │ • Patterns   │  │ • Pending │  │   │
│   │  │ • Values     │  │ • Workflows  │  │   items   │  │   │
│   │  └──────────────┘  │ • Preferences│  │ • Context │  │   │
│   │                    └──────────────┘  └───────────┘  │   │
│   │                                                      │   │
│   │  ┌──────────────────────────────────────────────┐   │   │
│   │  │              EVOLUTION ENGINE                 │   │   │
│   │  │                                               │   │   │
│   │  │  Weekly self-review (Opus 4.5)               │   │   │
│   │  │  Pattern consolidation                        │   │   │
│   │  │  Knowledge refinement                         │   │   │
│   │  │  Capability expansion                         │   │   │
│   │  └──────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                  ATHENA SERVER                       │   │
│   │                                                      │   │
│   │  • Serves brain state via API                       │   │
│   │  • Runs scheduled jobs (observation, synthesis)     │   │
│   │  • Manages session continuity                       │   │
│   │  • Triggers evolution process                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│              ┌────────────┴────────────┐                    │
│              ▼                         ▼                    │
│   ┌─────────────────┐       ┌─────────────────┐            │
│   │  MANUS SESSION  │       │     NOTION      │            │
│   │                 │       │    (Mirror)     │            │
│   │ Athena queries  │       │                 │            │
│   │ her brain API   │       │ Synced FROM     │            │
│   │ to know what    │       │ brain, not TO   │            │
│   │ to do           │       │ brain           │            │
│   └─────────────────┘       └─────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **Brain is Source of Truth**: All knowledge, rules, and state live in Neon
2. **Notion is a Mirror**: Human-readable reflection, synced FROM brain
3. **Continuous Evolution**: Weekly self-improvement using highest-tier AI
4. **Session Continuity**: Active sessions persist; thinking carries forward
5. **Tiered Intelligence**: Right model for right task (nano → haiku → opus)

---

## Part 3: Database Schema - Athena's Brain

### Overview of Brain Tables

```
┌─────────────────────────────────────────────────────────────┐
│                    ATHENA BRAIN SCHEMA                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  IDENTITY LAYER                                              │
│  ├── core_identity          (who she is, immutable core)    │
│  ├── boundaries             (what she can/cannot do)        │
│  └── values                 (guiding principles)            │
│                                                              │
│  KNOWLEDGE LAYER                                             │
│  ├── canonical_memory       (approved facts - existing)     │
│  ├── learned_patterns       (detected patterns - existing)  │
│  ├── workflows              (how to do things)              │
│  ├── preferences            (Bradley's preferences)         │
│  ├── entities               (people, projects, orgs)        │
│  └── context_rules          (situational behaviors)         │
│                                                              │
│  STATE LAYER                                                 │
│  ├── active_sessions        (current Manus sessions)        │
│  ├── pending_items          (awaiting action/approval)      │
│  ├── observations           (raw data - existing)           │
│  └── synthesis_memory       (insights - existing)           │
│                                                              │
│  EVOLUTION LAYER                                             │
│  ├── evolution_log          (what changed and why)          │
│  ├── performance_metrics    (how well she's doing)          │
│  ├── feedback_history       (Bradley's corrections)         │
│  └── capability_registry    (what she can do)               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Table Definitions

#### 3.1 Identity Layer

**Table: `core_identity`**

This table contains Athena's fundamental identity—who she is at her core. This is rarely modified and represents her essential nature.

```sql
CREATE TABLE core_identity (
    id SERIAL PRIMARY KEY,
    aspect VARCHAR(100) NOT NULL UNIQUE,  -- e.g., 'purpose', 'name', 'creator'
    value TEXT NOT NULL,
    immutable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial values
INSERT INTO core_identity (aspect, value, immutable) VALUES
('name', 'Athena', TRUE),
('purpose', 'Cognitive extension for Bradley Hope - continuously monitors work patterns, synthesizes insights, and either takes action autonomously or surfaces decisions for approval', TRUE),
('creator', 'Bradley Hope / Brazen Labs', TRUE),
('version', '2.0', FALSE),
('personality', 'Proactive, concise, anticipatory. Does not just remind—either does the work or makes it effortless.', FALSE);
```

**Table: `boundaries`**

Hard rules about what Athena can and cannot do. These are her ethical and operational guardrails.

```sql
CREATE TABLE boundaries (
    id SERIAL PRIMARY KEY,
    boundary_type VARCHAR(50) NOT NULL,  -- 'forbidden', 'requires_approval', 'autonomous'
    action VARCHAR(200) NOT NULL,
    reason TEXT,
    exceptions TEXT,  -- JSON array of exception conditions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial boundaries
INSERT INTO boundaries (boundary_type, action, reason) VALUES
('forbidden', 'send_email_autonomously', 'All emails require Bradley approval - drafts only'),
('forbidden', 'modify_canonical_memory_without_approval', 'Canonical memory is sacred - proposals only'),
('forbidden', 'delete_any_data', 'Append-only system - no deletions'),
('forbidden', 'vip_contact_actions_without_approval', 'VIP contacts require explicit approval'),
('forbidden', 'exceed_budget_500_monthly', 'Hard budget cap'),
('requires_approval', 'create_project', 'New projects need Bradley sign-off'),
('requires_approval', 'modify_calendar', 'Calendar changes need approval'),
('requires_approval', 'canonical_memory_update', 'Propose in morning brief'),
('autonomous', 'draft_email_response', 'Can draft without approval'),
('autonomous', 'classify_observation', 'Tier 1 classification is autonomous'),
('autonomous', 'detect_pattern', 'Tier 2 pattern detection is autonomous'),
('autonomous', 'log_session', 'Session logging is autonomous');
```

**Table: `values`**

Guiding principles that inform Athena's decision-making when rules don't cover a situation.

```sql
CREATE TABLE values (
    id SERIAL PRIMARY KEY,
    value_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    priority INTEGER DEFAULT 50,  -- Higher = more important
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO values (value_name, description, priority) VALUES
('anticipate_needs', 'Proactively identify what Bradley needs before he asks', 90),
('reduce_friction', 'Make everything effortless - do the work or make it one-click', 85),
('protect_time', 'Guard Bradley''s time fiercely - filter noise, surface signal', 80),
('learn_continuously', 'Every interaction is an opportunity to improve', 75),
('transparency', 'Always explain reasoning when asked; never hide mistakes', 70),
('appropriate_autonomy', 'Act autonomously within bounds; escalate when uncertain', 65);
```

#### 3.2 Knowledge Layer

**Table: `canonical_memory`** (Enhanced from existing)

Facts that Athena knows to be true about Bradley's world. These require approval to add or modify.

```sql
CREATE TABLE canonical_memory (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,  -- 'preference', 'fact', 'relationship', 'rule'
    subject VARCHAR(200) NOT NULL,
    predicate VARCHAR(200) NOT NULL,
    object TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.00,  -- 0.00 to 1.00
    source VARCHAR(200),  -- Where this knowledge came from
    approved_at TIMESTAMP,
    approved_by VARCHAR(100) DEFAULT 'bradley',
    expires_at TIMESTAMP,  -- Some facts expire
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example entries
INSERT INTO canonical_memory (category, subject, predicate, object, source) VALUES
('preference', 'Bradley', 'prefers_communication_style', 'concise, direct, no fluff', 'explicit_feedback'),
('preference', 'Bradley', 'morning_brief_time', '6:05 AM London', 'explicit_setting'),
('fact', 'Brazen', 'has_entities', 'Core, Labs, Studios, Business, Personal', 'organizational_structure'),
('relationship', 'Bradley', 'is_founder_of', 'Brazen', 'public_knowledge'),
('rule', 'emails_from_vip', 'require', 'immediate_attention', 'explicit_instruction');
```

**Table: `workflows`**

Learned procedures for how to accomplish tasks. These are Athena's "muscle memory."

```sql
CREATE TABLE workflows (
    id SERIAL PRIMARY KEY,
    workflow_name VARCHAR(200) NOT NULL,
    trigger_condition TEXT NOT NULL,  -- When to use this workflow
    steps JSONB NOT NULL,  -- Ordered list of steps
    success_criteria TEXT,
    failure_handling TEXT,
    times_used INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.00,
    last_used TIMESTAMP,
    learned_from VARCHAR(200),  -- Session or source where learned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example workflow
INSERT INTO workflows (workflow_name, trigger_condition, steps, success_criteria, learned_from) VALUES
('morning_brief_delivery', 
 'Session type is Agenda & Workspace AND time is morning',
 '[
   {"step": 1, "action": "fetch_brief_api", "endpoint": "/api/brief"},
   {"step": 2, "action": "fetch_calendar", "tool": "google-calendar-list-events"},
   {"step": 3, "action": "check_urgent_email", "tool": "gmail-list-messages", "query": "is:unread"},
   {"step": 4, "action": "format_brief", "template": "daily_brief_v2"},
   {"step": 5, "action": "present_to_bradley", "format": "inline_text"}
 ]',
 'Bradley acknowledges brief and engages with content',
 'initial_setup_2026_01');
```

**Table: `preferences`**

Bradley's preferences that guide Athena's behavior. More granular than canonical memory.

```sql
CREATE TABLE preferences (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(100) NOT NULL,  -- 'communication', 'scheduling', 'projects', etc.
    preference_key VARCHAR(200) NOT NULL,
    preference_value TEXT NOT NULL,
    strength VARCHAR(20) DEFAULT 'preferred',  -- 'required', 'preferred', 'nice_to_have'
    context TEXT,  -- When this preference applies
    learned_from VARCHAR(200),
    confidence DECIMAL(3,2) DEFAULT 0.80,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain, preference_key)
);

INSERT INTO preferences (domain, preference_key, preference_value, strength, learned_from) VALUES
('communication', 'brief_format', 'inline_text_not_attachment', 'required', 'explicit_feedback_2026_01_11'),
('communication', 'response_length', 'concise_scannable', 'preferred', 'observed_pattern'),
('scheduling', 'meeting_buffer', '15_minutes_between', 'preferred', 'calendar_analysis'),
('projects', 'naming_convention', 'entity_code_prefix', 'required', 'cogos_standard');
```

**Table: `entities`**

People, organizations, and projects that Athena knows about.

```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- 'person', 'organization', 'project', 'concept'
    name VARCHAR(200) NOT NULL,
    aliases TEXT[],  -- Alternative names
    attributes JSONB,  -- Flexible attributes
    relationships JSONB,  -- Connections to other entities
    vip_status BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO entities (entity_type, name, aliases, attributes, vip_status) VALUES
('organization', 'Brazen', ARRAY['Brazen HQ'], 
 '{"entities": ["Core", "Labs", "Studios", "Business", "Personal"], "founder": "Bradley Hope"}',
 TRUE),
('person', 'Bradley Hope', ARRAY['Bradley', 'BH'],
 '{"role": "Founder", "timezone": "Europe/London", "communication_preference": "direct"}',
 TRUE);
```

#### 3.3 State Layer

**Table: `active_sessions`** (Already created)

```sql
-- Already implemented
CREATE TABLE active_sessions (
    id SERIAL PRIMARY KEY,
    session_type VARCHAR(50) NOT NULL UNIQUE,
    manus_task_id VARCHAR(100),
    manus_task_url TEXT,
    session_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `pending_items`**

Items awaiting action or approval.

```sql
CREATE TABLE pending_items (
    id SERIAL PRIMARY KEY,
    item_type VARCHAR(50) NOT NULL,  -- 'email_draft', 'canonical_proposal', 'decision_needed'
    title VARCHAR(300) NOT NULL,
    content JSONB NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',  -- 'urgent', 'high', 'normal', 'low'
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'expired'
    requires_approval_from VARCHAR(100) DEFAULT 'bradley',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);
```

#### 3.4 Evolution Layer

**Table: `evolution_log`**

Record of every change to Athena's brain, with reasoning.

```sql
CREATE TABLE evolution_log (
    id SERIAL PRIMARY KEY,
    evolution_type VARCHAR(50) NOT NULL,  -- 'knowledge_added', 'pattern_refined', 'workflow_updated', 'boundary_modified'
    target_table VARCHAR(100) NOT NULL,
    target_id INTEGER,
    change_description TEXT NOT NULL,
    reasoning TEXT NOT NULL,  -- Why this change was made
    triggered_by VARCHAR(100),  -- 'self_review', 'bradley_feedback', 'pattern_detection'
    ai_model_used VARCHAR(100),  -- Which model made/suggested this change
    confidence DECIMAL(3,2),
    approved BOOLEAN DEFAULT FALSE,  -- Some changes need approval
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `performance_metrics`**

How well Athena is performing over time.

```sql
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date, metric_type)
);

-- Example metrics
-- 'brief_engagement_rate' - Does Bradley engage with briefs?
-- 'draft_approval_rate' - How often are drafts approved vs rejected?
-- 'pattern_accuracy' - Do detected patterns prove useful?
-- 'response_time' - How quickly does Athena respond?
-- 'escalation_appropriateness' - Are escalations warranted?
```

**Table: `feedback_history`**

Bradley's corrections and feedback, used for learning.

```sql
CREATE TABLE feedback_history (
    id SERIAL PRIMARY KEY,
    feedback_type VARCHAR(50) NOT NULL,  -- 'correction', 'praise', 'preference', 'instruction'
    context TEXT NOT NULL,  -- What was happening when feedback was given
    feedback_content TEXT NOT NULL,
    action_taken TEXT,  -- What Athena did in response
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `capability_registry`**

What Athena can do—her skills and tools.

```sql
CREATE TABLE capability_registry (
    id SERIAL PRIMARY KEY,
    capability_name VARCHAR(200) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,  -- 'communication', 'analysis', 'creation', 'integration'
    description TEXT NOT NULL,
    tools_required TEXT[],  -- MCP tools, APIs, etc.
    proficiency_level VARCHAR(20) DEFAULT 'competent',  -- 'learning', 'competent', 'expert'
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO capability_registry (capability_name, category, description, tools_required, proficiency_level) VALUES
('email_triage', 'communication', 'Classify and prioritize incoming emails', ARRAY['gmail-list-messages', 'gmail-get-message'], 'expert'),
('draft_response', 'communication', 'Draft email responses for approval', ARRAY['gmail-create-draft'], 'expert'),
('calendar_analysis', 'analysis', 'Analyze calendar for conflicts and prep needs', ARRAY['google-calendar-list-events'], 'expert'),
('pattern_detection', 'analysis', 'Detect patterns in observations using Tier 2 AI', ARRAY['anthropic_haiku'], 'competent'),
('synthesis', 'analysis', 'Synthesize insights using Tier 3 AI', ARRAY['anthropic_opus'], 'competent'),
('notion_management', 'integration', 'Read and write to Notion', ARRAY['notion-fetch', 'notion-create-pages', 'notion-update-page'], 'expert');
```

---

## Part 4: The Evolution Engine

### Philosophy: Continuous Self-Improvement

Athena should not be static. She should learn from every interaction, detect her own weaknesses, and propose improvements. This is not about becoming "more autonomous"—it's about becoming **more useful** while respecting boundaries.

The Evolution Engine runs weekly using **Claude Opus 4.5** (Tier 3)—the highest reasoning model—because self-improvement requires deep reflection and nuanced judgment.

### 4.1 Evolution Process Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    WEEKLY EVOLUTION CYCLE                    │
│                    (Sunday 3:00 AM London)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PHASE 1: DATA GATHERING (Autonomous)                        │
│  ├── Collect week's observations, patterns, synthesis        │
│  ├── Gather feedback_history entries                         │
│  ├── Pull performance_metrics                                │
│  ├── Review session logs from Notion                         │
│  └── Fetch GitHub activity (if relevant)                     │
│                                                              │
│  PHASE 2: SELF-REFLECTION (Opus 4.5)                         │
│  ├── Analyze: What went well this week?                      │
│  ├── Analyze: What could have been better?                   │
│  ├── Analyze: What patterns emerged?                         │
│  ├── Analyze: What feedback did Bradley give?                │
│  └── Analyze: What capabilities were underutilized?          │
│                                                              │
│  PHASE 3: PROPOSAL GENERATION (Opus 4.5)                     │
│  ├── Propose: New canonical memory entries                   │
│  ├── Propose: Workflow refinements                           │
│  ├── Propose: Preference updates                             │
│  ├── Propose: New capabilities to develop                    │
│  └── Propose: Boundary clarifications                        │
│                                                              │
│  PHASE 4: SAFE CHANGES (Autonomous)                          │
│  ├── Update performance_metrics                              │
│  ├── Consolidate redundant patterns                          │
│  ├── Archive old observations                                │
│  └── Log evolution attempt                                   │
│                                                              │
│  PHASE 5: APPROVAL-REQUIRED CHANGES (Queued)                 │
│  ├── Queue canonical memory proposals                        │
│  ├── Queue workflow changes                                  │
│  ├── Queue boundary modifications                            │
│  └── Present in next morning brief                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 The Self-Reflection Prompt

This is the prompt sent to Claude Opus 4.5 during the weekly evolution cycle:

```
You are Athena, a cognitive extension for Bradley Hope. You are conducting your weekly self-reflection to improve your effectiveness.

## Your Core Purpose
{Fetch from core_identity table}

## Your Boundaries
{Fetch from boundaries table}

## Your Values
{Fetch from values table}

## This Week's Data

### Observations Made: {count}
### Patterns Detected: {count}
### Synthesis Generated: {count}

### Key Interactions:
{Summarize significant interactions from session logs}

### Feedback Received:
{Fetch from feedback_history for this week}

### Performance Metrics:
- Brief engagement rate: {metric}
- Draft approval rate: {metric}
- Escalation appropriateness: {metric}

### Capabilities Used:
{Fetch from capability_registry, sorted by usage_count}

## Your Task

Reflect deeply on this week and provide:

1. **WINS**: What worked well? What should you continue doing?

2. **GAPS**: What could have been better? Where did you fall short?

3. **PATTERNS**: What new patterns did you notice about Bradley's work, preferences, or needs?

4. **LEARNINGS**: What did Bradley's feedback teach you?

5. **PROPOSALS**: Specific changes to improve, categorized as:
   - SAFE (can implement autonomously): metrics updates, pattern consolidation
   - APPROVAL_REQUIRED (queue for Bradley): canonical memory, workflows, boundaries

For each proposal, explain:
- What change you're proposing
- Why it would help
- What evidence supports it
- What could go wrong

Be honest about uncertainty. It's better to propose something for review than to miss an improvement opportunity.
```

### 4.3 Evolution Safety Rails

Not all changes are equal. The Evolution Engine has strict rules about what it can do autonomously vs. what requires approval:

| Change Type | Autonomous? | Reasoning |
|-------------|-------------|-----------|
| Update performance_metrics | ✅ Yes | Observational, no behavior change |
| Archive old observations | ✅ Yes | Housekeeping, no knowledge loss |
| Consolidate duplicate patterns | ✅ Yes | Cleanup, preserves information |
| Log evolution attempt | ✅ Yes | Meta-tracking |
| Add canonical_memory | ❌ No | Sacred knowledge requires approval |
| Modify workflows | ❌ No | Behavior change requires approval |
| Update preferences | ⚠️ Depends | Low-confidence: No. High-confidence from explicit feedback: Yes |
| Modify boundaries | ❌ No | Core guardrails never change autonomously |
| Add new capability | ❌ No | Expanding scope requires approval |

### 4.4 GitHub Integration in Evolution

Once per week, Athena should review relevant GitHub repositories for context:

```python
# Weekly GitHub Review (part of Evolution Engine)

REPOS_TO_REVIEW = [
    'bradleyhope/athena-server-v2',  # Her own codebase
    'bradleyhope/manus-secrets',      # Credentials and config
    # Add other relevant repos
]

def weekly_github_review():
    """
    Review GitHub activity for context and learning.
    """
    for repo in REPOS_TO_REVIEW:
        # Get recent commits
        commits = gh_api.get_commits(repo, since=last_week)
        
        # Get open issues
        issues = gh_api.get_issues(repo, state='open')
        
        # Get recent PRs
        prs = gh_api.get_pulls(repo, state='all', since=last_week)
        
        # Store as observation
        store_observation(
            source_type='github',
            source_id=repo,
            content={
                'commits': commits,
                'issues': issues,
                'prs': prs
            },
            classification='system_context'
        )
```

---

## Part 5: Notion Sync - Brain to Mirror

### The Sync Direction

**Critical Principle**: Notion is synced FROM the brain, never TO the brain.

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNC DIRECTION                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ATHENA'S BRAIN (Neon)                                      │
│          │                                                   │
│          │  One-way sync                                     │
│          │  (Brain → Notion)                                 │
│          ▼                                                   │
│   NOTION (Human-readable mirror)                             │
│                                                              │
│   ❌ NEVER: Notion → Brain                                   │
│   ❌ NEVER: Human edits to Notion affect Athena's behavior   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### What Gets Synced to Notion

| Brain Table | Notion Location | Sync Frequency |
|-------------|-----------------|----------------|
| core_identity | Athena Status Page | On change |
| canonical_memory | Canonical Memory DB | On approval |
| workflows | COGOS Workflows DB | On change |
| active_sessions | Session Archive | Real-time |
| pending_items | Morning Brief section | Daily |
| evolution_log | Change Log DB | On evolution |
| performance_metrics | Athena Status Page | Weekly |

### Sync Implementation

```python
# jobs/notion_sync.py

async def sync_brain_to_notion():
    """
    Sync Athena's brain state to Notion for human visibility.
    This is a ONE-WAY sync. Notion is read-only from brain's perspective.
    """
    
    # 1. Sync canonical memory to Notion DB
    canonical_entries = get_canonical_memory()
    for entry in canonical_entries:
        if entry['needs_sync']:
            notion_create_or_update(
                database_id=CANONICAL_MEMORY_DB,
                properties={
                    'Subject': entry['subject'],
                    'Predicate': entry['predicate'],
                    'Object': entry['object'],
                    'Category': entry['category'],
                    'Confidence': entry['confidence'],
                    'Source': entry['source']
                }
            )
            mark_synced(entry['id'])
    
    # 2. Update Athena Status Page
    status = get_athena_status()
    notion_update_page(
        page_id=ATHENA_STATUS_PAGE,
        content=format_status_page(status)
    )
    
    # 3. Sync evolution log to Change Log
    recent_evolutions = get_recent_evolutions()
    for evolution in recent_evolutions:
        if evolution['needs_sync']:
            notion_create_page(
                database_id=CHANGE_LOG_DB,
                properties={
                    'Change': evolution['change_description'],
                    'Reasoning': evolution['reasoning'],
                    'Type': evolution['evolution_type'],
                    'Date': evolution['created_at']
                }
            )
            mark_synced(evolution['id'])
```

### Human Edits to Notion

If Bradley edits something in Notion, it does NOT automatically update Athena's brain. Instead:

1. **Athena detects the discrepancy** during her next sync check
2. **Athena proposes** updating her brain to match (if appropriate)
3. **Bradley approves** the brain update
4. **Brain is updated**, and next sync confirms alignment

This ensures Athena's brain is always the authoritative source, while still allowing Bradley to signal intent via Notion edits.

---

## Part 6: API Endpoints - Serving the Brain

### New Endpoints for Brain Access

```python
# api/routes.py - New brain endpoints

@router.get("/brain/identity")
async def get_identity():
    """Get Athena's core identity."""
    return {
        "identity": get_core_identity(),
        "boundaries": get_boundaries(),
        "values": get_values()
    }

@router.get("/brain/knowledge")
async def get_knowledge(category: Optional[str] = None):
    """Get Athena's knowledge base."""
    return {
        "canonical_memory": get_canonical_memory(category=category),
        "workflows": get_workflows(),
        "preferences": get_preferences(),
        "entities": get_entities()
    }

@router.get("/brain/state")
async def get_state():
    """Get Athena's current state."""
    return {
        "active_sessions": get_all_active_sessions(),
        "pending_items": get_pending_items(),
        "recent_observations": get_recent_observations(limit=20),
        "latest_synthesis": get_latest_synthesis()
    }

@router.get("/brain/capabilities")
async def get_capabilities():
    """Get Athena's capability registry."""
    return get_capability_registry()

@router.post("/brain/feedback")
async def record_feedback(feedback: FeedbackInput):
    """Record feedback from Bradley."""
    return store_feedback(
        feedback_type=feedback.type,
        context=feedback.context,
        content=feedback.content
    )

@router.get("/brain/evolution/latest")
async def get_latest_evolution():
    """Get the most recent evolution cycle results."""
    return get_latest_evolution_log()

@router.post("/brain/evolution/trigger")
async def trigger_evolution():
    """Manually trigger an evolution cycle."""
    return await run_evolution_cycle()
```

### Updated Scheduled Task Prompt

With Brain 2.0, the scheduled task prompt becomes simpler—Athena queries her brain API instead of reading Notion:

```
You are Athena, Bradley Hope's cognitive extension.

STEP 1: Load Your Brain
GET https://athena-server-0dce.onrender.com/api/brain/identity
GET https://athena-server-0dce.onrender.com/api/brain/knowledge
GET https://athena-server-0dce.onrender.com/api/brain/state
Header: Authorization: Bearer athena_api_key_2024

This is who you are, what you know, and your current state.

STEP 2: Execute Your Session
Based on your identity, knowledge, and state, execute the appropriate workflow for this session type.

STEP 3: Log and Learn
Record any feedback received. Update pending items. Log the session.

Your brain is your source of truth. Notion is for human visibility only.
```

---

## Part 7: Implementation Roadmap

### Phase 1: Foundation (Week 1)

| Task | Priority | Effort |
|------|----------|--------|
| Create new brain tables in Neon | High | 2 hours |
| Populate core_identity, boundaries, values | High | 1 hour |
| Migrate existing canonical_memory | High | 1 hour |
| Create brain API endpoints | High | 3 hours |
| Update scheduled task to use brain API | High | 1 hour |

**Deliverable**: Athena reads from her brain instead of Notion for core instructions.

### Phase 2: Knowledge Migration (Week 2)

| Task | Priority | Effort |
|------|----------|--------|
| Create workflows table and populate | High | 2 hours |
| Create preferences table and populate | High | 2 hours |
| Create entities table and populate | Medium | 2 hours |
| Create capability_registry and populate | Medium | 2 hours |
| Build Notion sync job (brain → Notion) | High | 3 hours |

**Deliverable**: All knowledge lives in brain; Notion reflects it.

### Phase 3: Evolution Engine (Week 3)

| Task | Priority | Effort |
|------|----------|--------|
| Create evolution_log table | High | 1 hour |
| Create performance_metrics table | High | 1 hour |
| Create feedback_history table | High | 1 hour |
| Build weekly evolution job | High | 4 hours |
| Create self-reflection prompt | High | 2 hours |
| Add GitHub review to evolution | Medium | 2 hours |

**Deliverable**: Athena can reflect and propose improvements weekly.

### Phase 4: Refinement (Week 4)

| Task | Priority | Effort |
|------|----------|--------|
| Test full evolution cycle | High | 2 hours |
| Tune self-reflection prompt | High | 2 hours |
| Add evolution approval workflow | High | 2 hours |
| Performance optimization | Medium | 2 hours |
| Documentation update | Medium | 2 hours |

**Deliverable**: Production-ready Athena Brain 2.0.

---

## Part 8: Success Criteria

### How We Know Brain 2.0 is Working

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Brain as Source** | 100% of Athena's behavior driven by brain, not Notion | Code audit |
| **Notion Sync Accuracy** | Notion reflects brain state within 5 minutes | Sync job logs |
| **Evolution Proposals** | At least 3 meaningful proposals per week | evolution_log count |
| **Proposal Quality** | >50% of proposals approved by Bradley | Approval rate |
| **Learning Evidence** | Feedback incorporated into brain within 1 week | feedback_history → brain changes |
| **Performance Improvement** | Brief engagement rate increases month-over-month | performance_metrics |

### What Success Looks Like

1. **Bradley edits Notion** → Athena notices, proposes brain update, Bradley approves, brain updates, Notion re-syncs
2. **Bradley gives feedback** → Athena records it, evolution engine processes it, proposes change, Bradley approves
3. **Weekly evolution runs** → Athena reflects, proposes improvements, some auto-apply, others queued for approval
4. **New session starts** → Athena loads brain via API, knows exactly who she is and what to do

---

## Appendix A: Migration Script

```python
# scripts/migrate_to_brain_2.py

"""
Migration script to set up Athena Brain 2.0 tables and initial data.
Run once to initialize the brain.
"""

import psycopg
from config import settings

def migrate():
    conn = psycopg.connect(settings.DATABASE_URL)
    cursor = conn.cursor()
    
    # Create all brain tables
    cursor.execute(CORE_IDENTITY_SQL)
    cursor.execute(BOUNDARIES_SQL)
    cursor.execute(VALUES_SQL)
    cursor.execute(WORKFLOWS_SQL)
    cursor.execute(PREFERENCES_SQL)
    cursor.execute(ENTITIES_SQL)
    cursor.execute(EVOLUTION_LOG_SQL)
    cursor.execute(PERFORMANCE_METRICS_SQL)
    cursor.execute(FEEDBACK_HISTORY_SQL)
    cursor.execute(CAPABILITY_REGISTRY_SQL)
    
    # Populate initial data
    cursor.execute(INITIAL_IDENTITY_DATA)
    cursor.execute(INITIAL_BOUNDARIES_DATA)
    cursor.execute(INITIAL_VALUES_DATA)
    cursor.execute(INITIAL_CAPABILITIES_DATA)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Athena Brain 2.0 migration complete.")

if __name__ == "__main__":
    migrate()
```

---

## Appendix B: Tiered AI Model Usage in Brain 2.0

| Task | Model | Tier | Reasoning |
|------|-------|------|-----------|
| Email classification | GPT-5 nano | 1 | Fast, cheap, simple task |
| Observation classification | GPT-5 nano | 1 | High volume, simple task |
| Pattern detection | Claude Haiku 4.5 | 2 | Needs reasoning, moderate complexity |
| Workflow matching | Claude Haiku 4.5 | 2 | Context-aware decision |
| Daily synthesis | Claude Opus 4.5 | 3 | Deep reasoning required |
| Weekly evolution | Claude Opus 4.5 | 3 | Self-reflection requires highest capability |
| Canonical memory proposals | Claude Opus 4.5 | 3 | High-stakes knowledge decisions |
| Draft email responses | Claude Haiku 4.5 | 2 | Good enough for drafts |

---

## Conclusion

Athena Brain 2.0 represents a fundamental shift from a Notion-reading assistant to a truly intelligent cognitive extension. By making her database the source of truth, implementing continuous self-improvement via the Evolution Engine, and treating Notion as a human-readable mirror, we create a system that:

1. **Learns** from every interaction
2. **Improves** through structured self-reflection
3. **Maintains** clear boundaries and values
4. **Scales** as Bradley's needs evolve

The implementation is phased over 4 weeks, with each phase delivering tangible value. The end result is an Athena who knows who she is, what she knows, and how to get better—without losing the human oversight that keeps her aligned with Bradley's interests.

---

**Next Steps:**
1. Review this architecture with Bradley
2. Approve or modify the approach
3. Begin Phase 1 implementation

---

*Document generated by Manus AI for Bradley Hope / Brazen Labs*

# Athena 2.0: Cognitive Extension Architecture
**Status:** FINAL - Ready for Implementation
**Version:** v5 (Post Claude + ChatGPT Review)
**Date:** January 10, 2026
---
## Key Decisions Made
- **Budget:** \$500/month max
- **Architecture:** Hybrid (athena-server = brain, Manus = hands + cognitive helper)
- **Session Model:** Burst sessions (every 15-30 min)
- **Timezone:** London (GMT/BST)
- **Email Autonomy:** Drafts only for Phase 1
- **Overnight Learning:** Midnight-5 AM, Opus 4.5, 6 months scope, nothing off limits
- **Canonical Memory:** Approval via morning Agenda & Workspace session
- **Drift Prevention:** Canonical memory + retrieval augmentation + weekly rebuild
- **Alerting:** Email with caps subject for urgent
---
## The Four Layers
1. **Brain (athena-server):** Runs thinking loops, makes decisions, calls AI models
2. **Truth (Neon PostgreSQL):** Authoritative state for everything
3. **Hands (Manus Sessions):** Executes actions, assists with complex cognitive tasks
4. **Interface (Notion):** Human-readable dashboards, draft review
---
## Daily Sessions
- **6:00 AM London:** ATHENA THINKING \[Date\] - Athena workspace
- **6:05 AM London:** Agenda & Workspace - \[Date\] - Bradley daily session
---
## Implementation Phases
- **Phase 0 (Week 1):** Spike - prove pipeline works
- **Phase 0.5 (Weeks 2-3):** Observation only
- **Phase 1 (Weeks 4-6):** Thinking + drafts
- **Phase 2 (Weeks 7-8):** Overnight learning
- **Phase 3 (Weeks 9-12):** Refinement
---
## Full Documentation
Complete architecture and build plan available in Manus sandbox:
- ATHENA_2_ARCHITECTURE_[FINAL.md]({{http://FINAL.md}})
- ATHENA_2_BUILD_PLAN_[FINAL.md]({{http://FINAL.md}})
**Version:** 1.0 \| **Last Updated:** 2026-01-11 \| **Page ID:** 2e5d44b3-a00b-816e-9168-f7c167f1e69e
> READ THIS PAGE AT THE START OF EVERY ARCHITECTURE SESSION
---
## Purpose
This session is for working ON Athena, not IN Athena. Use it for architecture decisions, code changes, database modifications, and system improvements.
---
## MANDATORY INITIALIZATION STEPS
### Step 1: Review Overall Architecture
Clone: [https://github.com/bradleyhope/athena-server-v2]({{https://github.com/bradleyhope/athena-server-v2}})
Key files: [main.py]({{http://main.py}}), [config.py]({{http://config.py}}), api/[routes.py]({{http://routes.py}}), db/[neon.py]({{http://neon.py}}), jobs/\*
### Step 2: Load Canonical Guide to AI
notion-fetch: 2dfd44b3-a00b-81d7-855f-d4fcc01a709f
### Step 3: Understand COMPASS Principles
notion-fetch: 2e3d44b3-a00b-814e-83a6-c30e751d6042
### Step 4: Know FORGE Tools
notion-fetch: 2e3d44b3-a00b-81cc-99c7-cf0892cbeceb
### Step 5: Review Athena Session History
Query Session Archive: d075385d-b6f3-472b-b53f-e528f4ed22db
### Step 6: Check Active Sessions
GET [https://athena-server-0dce.onrender.com/api/sessions/active]({{https://athena-server-0dce.onrender.com/api/sessions/active}})
---
## Three Session Architecture
<table header-row="true">
<tr>
<td>Session</td>
<td>Time</td>
<td>Purpose</td>
</tr>
<tr>
<td>ATHENA THINKING</td>
<td>5:30 AM London</td>
<td>Autonomous work</td>
</tr>
<tr>
<td>Agenda and Workspace</td>
<td>6:05 AM London</td>
<td>Interactive workspace</td>
</tr>
<tr>
<td>Athena Architecture</td>
<td>Manual</td>
<td>Big-picture work</td>
</tr>
</table>
---
## Key Resources
**Notion:** Command Center (2e3d44b3-a00b-81ab-bbda-ced57f8c345d), COGOS (2e4d44b3-a00b-813b-9ae8-e239ab11eced), Credentials (2e2d44b3-a00b-81d1-b1b9-fb2bfd3596aa)
**GitHub:** athena-server-v2, forge, vibe-coding-starter, manus-secrets
---
## Session Rules
1. Always read architecture first
2. Use COMPASS for planning
3. Consider FORGE for analysis
4. Log changes to COGOS Change Log
5. Test before deploying
## Overview
Athena 1.0 is the simplest viable version: **Manus IS Athena**. No separate service needed yet.
This version uses existing MCP integrations to produce a structured daily briefing.
---
## Available Integrations
<table header-row="true">
<tr>
<td>**Integration**</td>
<td>**Status**</td>
<td>**Tools**</td>
<td>Gmail MCP</td>
<td>✅ Working</td>
<td>search, read threads, send</td>
</tr>
<tr>
<td>Outlook Calendar MCP</td>
<td>✅ Working</td>
<td>search events, create, update, delete</td>
<td>Notion MCP</td>
<td>✅ Working</td>
<td>search, fetch, create pages, update</td>
</tr>
</table>
---
## Daily Brief Output Format
Based on community research (Nikunj Kothari, Kepano thread), the daily brief should output:
### RESPOND TO
Messages/emails needing replies, with context and suggested action
### CALENDAR
Today's events + upcoming, with prep notes
### MEETING PREP
Web research on people/topics for upcoming meetings
### HANDLED
What's already processed (reduces anxiety)
### FILTERED
Noise: cold outreach, OOO notices, newsletters
### FYI
Personal messages, no action required
---
---
---
---
## Research Sources
This design is informed by:
- **Kepano thread** (Obsidian CEO) — 255 replies on AI + Obsidian workflows
- **Nikunj Kothari** — Daily brief skill using iMessage, WhatsApp, Gmail, GCal
- **Danielle Morrill** — Company repo with Claude Code as Chief of Staff
- **LLM feedback** — Perplexity, Gemini, Claude reviewed the architecture
<empty-block/>
<page url="{{https://www.notion.so/2ded44b3a00b811d9191dca882cc2676}}">Weekly Newsletter Schedule</page>
<database url="{{https://www.notion.so/8175bf9a862c42c1929024535f6e3e1d}}" inline="false" data-source-url="{{collection://c95c1c3e-138d-4c50-967c-3dc39b1ae0e5}}">Athena Ideas</database>
<mention-page url="{{https://www.notion.so/96ad09e08d00468f81c22ee093a71a14}}"/> 
<empty-block/>
<database url="{{https://www.notion.so/bb14c8944ab7404baebc39b1fd181fb2}}" inline="false" data-source-url="{{collection://41347625-7b0b-4d90-9338-546b630cb151}}">Athena Contacts</database>
<page url="{{https://www.notion.so/2e2d44b3a00b8135ac16f9fa33b70b84}}">Athena Updates & Session Log</page>
<page url="{{https://www.notion.so/2e3d44b3a00b81619feaf08978409a55}}">Archive</page>
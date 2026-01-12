**Version:** 3.0 \| **Status:** Active \| **Last Updated:** 2026-01-10
**GitHub:** [https://github.com/bradleyhope/cogos-system]({{https://github.com/bradleyhope/cogos-system}})
---
## 1. Philosophy and Aspiration
COGOS is the single source of truth for the entire Brazen digital ecosystem. It is a living system designed for both humans and AI agents to understand, navigate, and safely modify the workspace. Its aspiration is to create a self-documenting, self-regulating and even self-improving environment where every component is discoverable, every workflow is explicit, and every change is intentional and interconnected.
This is not just a collection of pages; it is the cognitive map of the workspace. It provides the context, rules, and architecture that enable agents like Manus to operate effectively and safely, while providing humans with a clear, organized, and aesthetically pleasing environment.
---
## 2. The Architecture
<table header-row="true">
<tr>
<td>Component</td>
<td>Page ID</td>
<td>Purpose</td>
</tr>
<tr>
<td>COGOS Page</td>
<td>2e4d44b3-a00b-813b-9ae8-e239ab11eced</td>
<td>This page. Ground zero.</td>
</tr>
<tr>
<td><mention-page url="{{https://www.notion.so/2e4d44b3a00b81889f62f277e147fe4f}}"/></td>
<td>2e4d44b3-a00b-8188-9f62-f277e147fe4f</td>
<td>Entry point for all Manus sessions.</td>
</tr>
<tr>
<td>[Agent Rulebook]({{/2e3d44b3a00b814b83a9f0e035b5f617?pvs=25}})</td>
<td>2e3d44b3-a00b-814b-83a9-f0e035b5f617</td>
<td>Safety rules for all agents.</td>
</tr>
<tr>
<td><mention-database url="{{https://www.notion.so/8a844a786c604b96a4d2dc3b45b4f430}}"/></td>
<td>7fcd9c7c-a9b0-4a8e-b8f0-3c5d6e7f8a9b</td>
<td>Immutable record of all system changes.</td>
</tr>
</table>
---
## 3. How COGOS Works
Every session begins with `cogos init`. Manus reads the page, determines Task Type and Entity via Session Routing, and loads context from the appropriate Entity Hub.
The **End Session Workflow** captures discoveries and feeds into the **Universal Edit Process** - the standard procedure for making any change to any page.
<empty-block/>
---
## 4. The Universal Edit Process
**Trigger:** Manus proposes a change to ANY page, or user says "edit mode".
1. State Awareness - Read COGOS first
2. Propose Changes - Explain rationale
3. User Approval - Human-in-the-loop
4. Implementation - Execute approved changes
5. Logging - Log to Change Log
6. GitHub Sync - Push to repo
7. Version Increment
### Page Editing Checklist
- All tables have Page IDs or links
- Version numbers are consistent
- No duplicate sections
- All links are functional
---
## 5. System State Map
### 5.1 Core Pages
<table header-row="true">
<tr>
<td>Page</td>
<td>Page ID</td>
</tr>
<tr>
<td>COGOS</td>
<td>2e4d44b3-a00b-813b-9ae8-e239ab11eced</td>
</tr>
<tr>
<td>Manus Init</td>
<td>2e4d44b3-a00b-8188-9f62-f277e147fe4f</td>
</tr>
<tr>
<td>Athena Init</td>
<td>2e4d44b3-a00b-819c-98bd-cb85db3fddd5</td>
</tr>
<tr>
<td>Agent Rulebook</td>
<td>2e3d44b3-a00b-814b-83a9-f0e035b5f617</td>
</tr>
<tr>
<td>Brainstorm Manager</td>
<td>2e4d44b3-a00b-81e0-99c6-e8a4bd9cf380</td>
</tr>
<tr>
<td>Project Manager</td>
<td>2e4d44b3-a00b-81b4-9d7f-f2e19510fe25</td>
</tr>
</table>
### 6.2 Databases
<table header-row="true">
<tr>
<td>Database</td>
<td>Data Source ID</td>
</tr>
<tr>
<td>Projects</td>
<td>de557503-871f-4a35-9754-826c16e0ea88</td>
</tr>
<tr>
<td>[Athena Tasks]({{/da83083324864a76ad959578dbbbd4d0?pvs=25}})</td>
<td>44aa96e7-eb95-45ac-9b28-f3bfffec6802</td>
</tr>
<tr>
<td>[Session Archive]({{/7fe5268e17a744f8bff347a080f1015b?pvs=25}})</td>
<td>d075385d-b6f3-472b-b53f-e528f4ed22db</td>
</tr>
<tr>
<td>Change Log</td>
<td>7fcd9c7c-a9b0-4a8e-b8f0-3c5d6e7f8a9b</td>
</tr>
<tr>
<td>Brainstorm</td>
<td>d1b506d9-4b2a-4a46-8037-c71b3fa8e185</td>
</tr>
<tr>
<td>COGOS Workflows</td>
<td>b8fe6cdd-3cba-4e2f-ba18-d6eac081a7b5</td>
</tr>
<tr>
<td>COGOS Knowledge Index</td>
<td>6a6b7c7d-861b-4aee-8f34-25324c7d1ae4</td>
</tr>
<tr>
<td>Personal Items</td>
<td>a38d5418-6988-40a0-9cb8-fee3c2811e8e</td>
</tr>
<tr>
<td>[Credentials]({{/8784577f54fe4ef6a68bd44e9e084087?pvs=25}})</td>
<td></td>
</tr>
</table>
### 6.3 Entity Hubs
<table header-row="true">
<tr>
<td>Entity</td>
<td>Code</td>
<td>Page ID</td>
</tr>
<tr>
<td>Brazen Core</td>
<td>C</td>
<td>2e3d44b3-a00b-818b-8e6e-f6b1ac833f72</td>
</tr>
<tr>
<td>Brazen Labs</td>
<td>L</td>
<td>1edd44b3-a00b-80bc-a4e3-e016ce400b44</td>
</tr>
<tr>
<td>Brazen Studios</td>
<td>S</td>
<td>a3ef158e-01ae-4694-a25b-c74a804ed658</td>
</tr>
<tr>
<td>Business</td>
<td>B</td>
<td>5036212c-d603-4539-ab18-c9009f0e4a90</td>
</tr>
<tr>
<td>Personal</td>
<td>P</td>
<td>2e4d44b3-a00b-810c-88e3-ed3da17bd3c4</td>
</tr>
</table>
### 6.4 Tools (Init Commands)
<table header-row="true">
<tr>
<td>Command</td>
<td>Tool</td>
<td>Page ID</td>
</tr>
<tr>
<td>init forge</td>
<td>FORGE</td>
<td>2e3d44b3-a00b-81cc-99c7-cf0892cbeceb</td>
</tr>
<tr>
<td>init athena</td>
<td>ATHENA</td>
<td>2e3d44b3-a00b-81ab-bbda-ced57f8c345d</td>
</tr>
<tr>
<td>init argus</td>
<td>ARGUS</td>
<td>2cbd44b3-a00b-8140-b54e-cb083709f01b</td>
</tr>
<tr>
<td>init compass</td>
<td>COMPASS</td>
<td>2e3d44b3-a00b-814e-83a6-c30e751d6042</td>
</tr>
<tr>
<td>init hollywood</td>
<td>Hollywood Suite</td>
<td>2dad44b3-a00b-81dc-8ed2-d2ea57a3ea19</td>
</tr>
<tr>
<td>init whale</td>
<td>Whale Hunting</td>
<td>2cbd44b3-a00b-81a3-bd6d-e3d0086df7a8</td>
</tr>
<tr>
<td>init closer</td>
<td>The Closer</td>
<td>2cbd44b3-a00b-81ba-870f-c1a2cb22b56c</td>
</tr>
<tr>
<td>init signal</td>
<td>Hollywood Signal</td>
<td>2cbd44b3-a00b-81bc-a1da-e2d5bff7c3e0</td>
</tr>
<tr>
<td>init personal</td>
<td>Personal</td>
<td>2e4d44b3-a00b-810c-88e3-ed3da17bd3c4</td>
</tr>
</table>
### 6.5 COGOS Workflows
<table header-row="true">
<tr>
<td>Workflow</td>
<td>Page ID</td>
</tr>
<tr>
<td>End Session Workflow</td>
<td>2e4d44b3-a00b-81f4-a0fa-dac7d1c9db7b</td>
</tr>
<tr>
<td>Workflow Workflow</td>
<td>2e4d44b3-a00b-815a-8b04-d2347f3caec7</td>
</tr>
<tr>
<td>Page Improvement Process</td>
<td>2e4d44b3-a00b-81a1-93e5-e18d66c49acb</td>
</tr>
<tr>
<td>Credentials Update</td>
<td>2e4d44b3-a00b-81f3-8edb-cd2fe305a12a</td>
</tr>
<tr>
<td>Manus Knowledge Optimization</td>
<td>2e4d44b3-a00b-81aa-9d06-d1c70a0937bd</td>
</tr>
</table>
---
## 7. Rules and Constraints
### 7.1 Protection Tiers
<table header-row="true">
<tr>
<td>Tier</td>
<td>Access Level</td>
<td>Examples</td>
</tr>
<tr>
<td>Tier 0</td>
<td>READ ONLY</td>
<td>Credentials, Personal, Financial</td>
</tr>
<tr>
<td>Tier 1</td>
<td>READ + APPEND</td>
<td>COGOS, Change Log</td>
</tr>
<tr>
<td>Tier 2</td>
<td>READ + WRITE</td>
<td>Most pages</td>
</tr>
<tr>
<td>Tier 3</td>
<td>FULL ACCESS</td>
<td>Drafts, sandbox</td>
</tr>
</table>
### 7.2 Core Rules
1. NEVER delete pages
2. ALWAYS log changes
3. CHECK protection tier
4. APPEND, don't replace
5. ASK before bulk changes (5+)
---
## 8. Session Routing
<table header-row="true">
<tr>
<td>Code</td>
<td>Meaning</td>
</tr>
<tr>
<td>N</td>
<td>New project</td>
</tr>
<tr>
<td>E</td>
<td>Existing project</td>
</tr>
<tr>
<td>Q</td>
<td>Quick task</td>
</tr>
<tr>
<td>D</td>
<td>Discussion</td>
</tr>
<tr>
<td>I</td>
<td>Investigation</td>
</tr>
<tr>
<td>A</td>
<td>Action</td>
</tr>
<tr>
<td>C/L/S/B/P</td>
<td>Core/Labs/Studios/Business/Personal</td>
</tr>
</table>
---
## 9. Credentials & Secrets
- **Credentials Registry** (Notion) = metadata only
- **manus-secrets** (GitHub) = actual secrets
```javascript
gh repo clone bradleyhope/manus-secrets
source manus-secrets/.env
```
---
## 10. Reference Card
**Full documentation:** [https://github.com/bradleyhope/cogos-system/blob/master/COGOS_V3_MASTER.md]({{https://github.com/bradleyhope/cogos-system/blob/master/COGOS_V3_MASTER.md}})
**Manus Knowledge:** [https://github.com/bradleyhope/cogos-system/blob/master/MANUS_KNOWLEDGE_COGOS_V2_CONDENSED.txt]({{https://github.com/bradleyhope/cogos-system/blob/master/MANUS_KNOWLEDGE_COGOS_V2_CONDENSED.txt}})
---
## 11. Version History
<table header-row="true">
<tr>
<td>Version</td>
<td>Date</td>
<td>Changes</td>
</tr>
<tr>
<td>2.0</td>
<td>2026-01-10</td>
<td>Initial COGOS v2</td>
</tr>
<tr>
<td>2.1</td>
<td>2026-01-10</td>
<td>Added workflows</td>
</tr>
<tr>
<td>2.2</td>
<td>2026-01-10</td>
<td>Added Personal entity</td>
</tr>
<tr>
<td>2.3</td>
<td>2026-01-10</td>
<td>Optimized Reference Card</td>
</tr>
<tr>
<td>2.4</td>
<td>2026-01-10</td>
<td>Added How COGOS Works</td>
</tr>
<tr>
<td>3.0</td>
<td>2026-01-10</td>
<td>Full restructure with Page IDs</td>
</tr>
</table>
<empty-block/>
Nested Pages
<page url="{{https://www.notion.so/2e4d44b3a00b81889f62f277e147fe4f}}">COGOS Init</page>
<database url="{{https://www.notion.so/8a844a786c604b96a4d2dc3b45b4f430}}" inline="false" icon="🪢" data-source-url="{{collection://7fcd45fa-7897-493a-ab24-fdf7bbbdc0e3}}">Change Log</database>
<page url="{{https://www.notion.so/2e4d44b3a00b81e099c6e8a4bd9cf380}}">Brainstorm Manager</page>
<database url="{{https://www.notion.so/b8fe6cdd3cba4e2fba18d6eac081a7b5}}" inline="false" icon="🍊" data-source-url="{{collection://991a69f1-6847-44d2-b95a-18f5ab5242b4}}">COGOS Workflows</database>
<database url="{{https://www.notion.so/be151d431458491eb764694177bb6b91}}" inline="false" data-source-url="{{collection://cda1e8be-8ced-4a33-92af-0dfa41014efe}}">Workflow Registry</database>
<database url="{{https://www.notion.so/fb07d28e09a94714897ada5af61fad78}}" inline="false" data-source-url="{{collection://fddf5e2c-e48b-4892-b56d-4feecbe26e2f}}">Improvement Tracker</database>
<database url="{{https://www.notion.so/2455b84ded6d43ae91fd85ea0dd263d3}}" inline="false" data-source-url="{{collection://6a0258f5-1904-48b6-a6fb-d6a7575a21b1}}">Anti-Pattern Log</database>
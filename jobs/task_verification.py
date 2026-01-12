"""
Task Verification Module for ATHENA THINKING

Verifies and enriches tasks logged by Gemini, filters noise,
and generates daily impressions.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger("athena.task_verification")

# Notion API configuration
NOTION_VERSION = "2022-06-28"


class TaskVerifier:
    """Verifies and enriches tasks from Gemini."""
    
    def __init__(self):
        self.notion_headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    async def get_unverified_tasks(self) -> list:
        """
        Query Athena Tasks DB for recent Gemini-logged tasks.
        Looks for: Source=Email, Status=Not Started (unverified)
        """
        if not settings.NOTION_API_KEY:
            logger.warning("NOTION_API_KEY not set, skipping task verification")
            return []

        url = f"https://api.notion.com/v1/databases/{settings.ATHENA_TASKS_DB_ID}/query"
        
        # Filter for unverified email-sourced tasks
        filter_payload = {
            "filter": {
                "and": [
                    {
                        "property": "Source",
                        "select": {
                            "equals": "Email"
                        }
                    },
                    {
                        "property": "Status",
                        "select": {
                            "equals": "Not Started"
                        }
                    }
                ]
            },
            "sorts": [
                {
                    "timestamp": "created_time",
                    "direction": "descending"
                }
            ],
            "page_size": 50
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.notion_headers,
                    json=filter_payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                tasks = []
                for page in data.get("results", []):
                    task = self._parse_task_page(page)
                    if task:
                        tasks.append(task)
                
                logger.info(f"Found {len(tasks)} unverified tasks")
                return tasks
                
        except Exception as e:
            logger.error(f"Error querying Athena Tasks: {e}")
            return []
    
    def _parse_task_page(self, page: dict) -> Optional[dict]:
        """Parse a Notion page into a task dict."""
        try:
            props = page.get("properties", {})
            
            # Extract title
            title_prop = props.get("Task", {})
            title = ""
            if title_prop.get("title"):
                title = title_prop["title"][0]["plain_text"] if title_prop["title"] else ""
            
            # Extract other properties
            context = ""
            context_prop = props.get("Context", {})
            if context_prop.get("rich_text"):
                context = context_prop["rich_text"][0]["plain_text"] if context_prop["rich_text"] else ""
            
            person = ""
            person_prop = props.get("Person", {})
            if person_prop.get("rich_text"):
                person = person_prop["rich_text"][0]["plain_text"] if person_prop["rich_text"] else ""
            
            priority = props.get("Priority", {}).get("select", {}).get("name", "")
            task_type = props.get("Type", {}).get("select", {}).get("name", "")
            
            due_date = None
            due_prop = props.get("Due", {}).get("date")
            if due_prop:
                due_date = due_prop.get("start")
            
            return {
                "id": page["id"],
                "title": title,
                "context": context,
                "person": person,
                "priority": priority,
                "type": task_type,
                "due": due_date,
                "created": page.get("created_time")
            }
        except Exception as e:
            logger.error(f"Error parsing task page: {e}")
            return None
    
    async def verify_task(self, task: dict, email_context: str = "") -> dict:
        """
        Use AI to verify if a task is actionable and enrich it.
        
        Returns:
            {
                "keep": bool,
                "reason": str,
                "enriched": {
                    "context": str,
                    "priority": str,
                    "type": str,
                    "person": str
                }
            }
        """
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set, auto-keeping task")
            return {"keep": True, "reason": "No AI verification available", "enriched": {}}
        
        prompt = f"""Analyze this task extracted from an email and determine if it's a real actionable task for Bradley.

TASK: {task['title']}
CONTEXT: {task.get('context', 'None')}
PERSON: {task.get('person', 'Unknown')}
CURRENT PRIORITY: {task.get('priority', 'Not set')}
CURRENT TYPE: {task.get('type', 'Not set')}

VERIFICATION CRITERIA:
- KEEP if: Clear action required from Bradley, has deadline, involves important contact, related to active project
- DISCARD if: Newsletter/marketing, FYI only, already completed, duplicate, spam/irrelevant

Respond in JSON format:
{{
    "keep": true/false,
    "reason": "Brief explanation",
    "enriched": {{
        "context": "Enhanced context if keeping",
        "priority": "High/Medium/Low",
        "type": "Email/Call/Meeting/Task/Review/Admin",
        "person": "Identified person name if any"
    }}
}}"""

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            logger.info(f"Task '{task['title'][:30]}...' verified: keep={result.get('keep')}")
            return result
            
        except Exception as e:
            logger.error(f"Error verifying task: {e}")
            return {"keep": True, "reason": f"Verification error: {e}", "enriched": {}}
    
    async def update_task_status(self, task_id: str, keep: bool, enriched: dict = None, reason: str = "") -> bool:
        """
        Update task in Notion based on verification result.
        - KEEP: Update status to "To Do", add enriched context
        - DISCARD: Update status to "Done", add reason in context
        """
        if not settings.NOTION_API_KEY:
            return False
        
        url = f"https://api.notion.com/v1/pages/{task_id}"
        
        properties = {}
        
        if keep:
            properties["Status"] = {"select": {"name": "To Do"}}
            if enriched:
                if enriched.get("context"):
                    properties["Context"] = {
                        "rich_text": [{"text": {"content": enriched["context"][:2000]}}]
                    }
                if enriched.get("priority"):
                    properties["Priority"] = {"select": {"name": enriched["priority"]}}
                if enriched.get("type"):
                    properties["Type"] = {"select": {"name": enriched["type"]}}
                if enriched.get("person"):
                    properties["Person"] = {
                        "rich_text": [{"text": {"content": enriched["person"][:200]}}]
                    }
        else:
            properties["Status"] = {"select": {"name": "Done"}}
            properties["Context"] = {
                "rich_text": [{"text": {"content": f"[Auto-discarded] {reason}"[:2000]}}]
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers=self.notion_headers,
                    json={"properties": properties},
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"Updated task {task_id}: keep={keep}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False


class ImpressionGenerator:
    """Generates daily impressions from email/calendar data."""
    
    async def generate_impressions(self, emails: list, calendar_events: list, verified_tasks: list) -> list:
        """
        Generate high-level impressions from the day's data.
        
        Returns list of impressions:
        [
            {
                "category": "relationship|opportunity|risk|theme",
                "content": "The impression text",
                "confidence": 0.0-1.0,
                "sources": ["email_id_1", "email_id_2"]
            }
        ]
        """
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set, skipping impression generation")
            return []
        
        # Prepare summary of data
        email_summary = self._summarize_emails(emails)
        calendar_summary = self._summarize_calendar(calendar_events)
        task_summary = self._summarize_tasks(verified_tasks)
        
        prompt = f"""Analyze today's data and generate strategic impressions for Bradley.

EMAIL SUMMARY:
{email_summary}

CALENDAR SUMMARY:
{calendar_summary}

VERIFIED TASKS:
{task_summary}

Generate 3-5 high-level impressions. Focus on:
1. RELATIONSHIP signals - who's active, who's silent, new contacts
2. OPPORTUNITY signals - business opportunities, meeting requests
3. RISK signals - urgent items, approaching deadlines, conflicts
4. THEME signals - patterns across communications

DO NOT list individual tasks. Focus on strategic observations.

Respond in JSON format:
{{
    "impressions": [
        {{
            "category": "relationship|opportunity|risk|theme",
            "content": "The strategic observation",
            "confidence": 0.0-1.0
        }}
    ]
}}"""

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            impressions = result.get("impressions", [])
            logger.info(f"Generated {len(impressions)} impressions")
            return impressions
            
        except Exception as e:
            logger.error(f"Error generating impressions: {e}")
            return []
    
    def _summarize_emails(self, emails: list) -> str:
        """Create a brief summary of emails for the prompt."""
        if not emails:
            return "No emails to summarize"
        
        summary_parts = []
        for email in emails[:20]:  # Limit to 20 most recent
            sender = email.get("from", "Unknown")
            subject = email.get("subject", "No subject")
            summary_parts.append(f"- From: {sender}, Subject: {subject}")
        
        return "\n".join(summary_parts)
    
    def _summarize_calendar(self, events: list) -> str:
        """Create a brief summary of calendar events."""
        if not events:
            return "No calendar events"
        
        summary_parts = []
        for event in events[:10]:
            title = event.get("title", "Untitled")
            time = event.get("start", "Unknown time")
            summary_parts.append(f"- {title} at {time}")
        
        return "\n".join(summary_parts)
    
    def _summarize_tasks(self, tasks: list) -> str:
        """Create a brief summary of verified tasks."""
        if not tasks:
            return "No verified tasks"
        
        kept = [t for t in tasks if t.get("kept")]
        discarded = [t for t in tasks if not t.get("kept")]
        
        return f"Kept: {len(kept)}, Discarded: {len(discarded)}"


async def run_task_verification(emails: list = None, calendar_events: list = None) -> dict:
    """
    Main entry point for task verification.
    Called by ATHENA THINKING job.
    
    Returns:
        {
            "verified_tasks": [...],
            "impressions": [...],
            "stats": {
                "total": int,
                "kept": int,
                "discarded": int
            }
        }
    """
    logger.info("Starting task verification...")
    
    verifier = TaskVerifier()
    impression_gen = ImpressionGenerator()
    
    # Get unverified tasks
    unverified_tasks = await verifier.get_unverified_tasks()
    
    verified_results = []
    stats = {"total": len(unverified_tasks), "kept": 0, "discarded": 0}
    
    # Verify each task
    for task in unverified_tasks:
        result = await verifier.verify_task(task)
        
        # Update in Notion
        await verifier.update_task_status(
            task["id"],
            keep=result.get("keep", True),
            enriched=result.get("enriched", {}),
            reason=result.get("reason", "")
        )
        
        verified_results.append({
            "task": task,
            "kept": result.get("keep", True),
            "reason": result.get("reason", ""),
            "enriched": result.get("enriched", {})
        })
        
        if result.get("keep", True):
            stats["kept"] += 1
        else:
            stats["discarded"] += 1
    
    # Generate impressions
    impressions = await impression_gen.generate_impressions(
        emails or [],
        calendar_events or [],
        verified_results
    )
    
    logger.info(f"Task verification complete: {stats}")
    
    return {
        "verified_tasks": verified_results,
        "impressions": impressions,
        "stats": stats
    }

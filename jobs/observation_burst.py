"""
Athena Server v2 - Observation Burst Job
Tier 1: Collect and classify observations from Gmail and Calendar.
Uses GPT-5 nano for classification.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
import json

from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings
from db.neon import store_observation, db_cursor

logger = logging.getLogger("athena.jobs.observation")


def get_google_credentials() -> Credentials:
    """Get Google OAuth credentials."""
    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )


def classify_email(client: OpenAI, email: dict) -> dict:
    """
    Classify an email using GPT-5 nano.
    
    Returns classification with category, priority, and summary.
    """
    prompt = f"""Classify this email for Bradley Hope's cognitive assistant.

From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No subject')}
Snippet: {email.get('snippet', '')[:500]}

Respond in JSON format:
{{
    "category": "one of: urgent_action, financial, newsletter, automated, personal, work, promotional",
    "priority": "one of: urgent, high, normal, low",
    "summary": "one sentence summary",
    "requires_response": true/false,
    "action_needed": "brief description or null"
}}"""

    try:
        response = client.chat.completions.create(
            model=settings.TIER1_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=200,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            "category": "unknown",
            "priority": "normal",
            "summary": email.get('subject', 'Unknown email'),
            "requires_response": False,
            "action_needed": None
        }


def classify_event(client: OpenAI, event: dict) -> dict:
    """
    Classify a calendar event using GPT-5 nano.
    
    Returns classification with category, priority, and summary.
    """
    prompt = f"""Classify this calendar event for Bradley Hope's cognitive assistant.

Title: {event.get('summary', 'Untitled')}
Start: {event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Unknown'))}
Location: {event.get('location', 'No location')}
Description: {event.get('description', 'No description')[:300]}

Respond in JSON format:
{{
    "category": "one of: meeting, deadline, personal, travel, recurring, reminder",
    "priority": "one of: urgent, high, normal, low",
    "summary": "one sentence summary",
    "preparation_needed": "brief description or null"
}}"""

    try:
        response = client.chat.completions.create(
            model=settings.TIER1_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=150,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Event classification failed: {e}")
        return {
            "category": "meeting",
            "priority": "normal",
            "summary": event.get('summary', 'Calendar event'),
            "preparation_needed": None
        }


def collect_gmail_observations(client: OpenAI) -> List[Dict]:
    """Collect and classify recent emails."""
    observations = []
    
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        # Get unread emails from the last hour
        results = service.users().messages().list(
            userId='me',
            q='is:unread newer_than:1h',
            maxResults=20
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} unread emails")
        
        for msg in messages:
            # Get full message
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
            
            email_data = {
                'id': msg['id'],
                'from': headers.get('From', 'Unknown'),
                'subject': headers.get('Subject', 'No subject'),
                'date': headers.get('Date', ''),
                'snippet': full_msg.get('snippet', '')
            }
            
            # Classify with GPT-5 nano
            classification = classify_email(client, email_data)
            
            observation = {
                'source': 'gmail',
                'source_id': msg['id'],
                'observed_at': datetime.utcnow(),
                'category': classification['category'],
                'priority': classification['priority'],
                'summary': classification['summary'],
                'raw_content': json.dumps(email_data),
                'metadata': json.dumps({
                    'from': email_data['from'],
                    'subject': email_data['subject'],
                    'requires_response': classification.get('requires_response', False),
                    'action_needed': classification.get('action_needed')
                })
            }
            
            observations.append(observation)
            
    except Exception as e:
        logger.error(f"Gmail collection failed: {e}")
    
    return observations


def collect_calendar_observations(client: OpenAI) -> List[Dict]:
    """Collect and classify upcoming calendar events."""
    observations = []
    
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)
        
        # Get events for the next 7 days
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=7)).isoformat() + 'Z'
        
        results = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=30,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = results.get('items', [])
        logger.info(f"Found {len(events)} upcoming events")
        
        for event in events:
            # Classify with GPT-5 nano
            classification = classify_event(client, event)
            
            start = event.get('start', {})
            start_time = start.get('dateTime', start.get('date', ''))
            
            observation = {
                'source': 'calendar',
                'source_id': event['id'],
                'observed_at': datetime.utcnow(),
                'category': classification['category'],
                'priority': classification['priority'],
                'summary': classification['summary'],
                'raw_content': json.dumps({
                    'title': event.get('summary', 'Untitled'),
                    'start': start_time,
                    'location': event.get('location'),
                    'description': event.get('description', '')[:500]
                }),
                'metadata': json.dumps({
                    'event_start': start_time,
                    'preparation_needed': classification.get('preparation_needed')
                })
            }
            
            observations.append(observation)
            
    except Exception as e:
        logger.error(f"Calendar collection failed: {e}")
    
    return observations


async def run_observation_burst():
    """
    Run a complete observation burst.
    Collects from Gmail and Calendar, classifies with GPT-5 nano, stores to Neon.
    """
    logger.info("Starting observation burst...")
    start_time = datetime.utcnow()
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )
    
    # Collect observations
    gmail_obs = collect_gmail_observations(client)
    calendar_obs = collect_calendar_observations(client)
    
    all_observations = gmail_obs + calendar_obs
    
    # Store to database
    stored_count = 0
    for obs in all_observations:
        try:
            store_observation(obs)
            stored_count += 1
        except Exception as e:
            logger.error(f"Failed to store observation: {e}")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Observation burst complete: {stored_count} observations stored in {duration:.1f}s")
    
    return {
        "gmail_count": len(gmail_obs),
        "calendar_count": len(calendar_obs),
        "stored_count": stored_count,
        "duration_seconds": duration
    }

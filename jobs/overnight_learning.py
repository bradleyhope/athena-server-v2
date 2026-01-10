"""
Athena Server v2 - Overnight Learning Job
Reads historical emails and past Manus sessions during midnight-5 AM.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
import json

from anthropic import Anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings
from db.neon import store_observation, db_cursor

logger = logging.getLogger("athena.jobs.overnight")


def get_learning_progress() -> Dict:
    """Get current overnight learning progress."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT source, MAX(last_processed_id) as last_id, 
                   MAX(last_processed_date) as last_date,
                   SUM(items_processed) as total_processed
            FROM deep_learning_progress
            GROUP BY source
        """)
        results = cursor.fetchall()
        return {r['source']: r for r in results}


def update_learning_progress(source: str, last_id: str, items_processed: int):
    """Update learning progress for a source."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO deep_learning_progress (source, last_processed_id, last_processed_date, items_processed)
            VALUES (%s, %s, %s, %s)
        """, (source, last_id, datetime.utcnow(), items_processed))


def get_google_credentials() -> Credentials:
    """Get Google OAuth credentials."""
    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )


def read_historical_emails(client: Anthropic, batch_size: int = 20) -> int:
    """
    Read historical emails and extract insights.
    Returns number of emails processed.
    """
    progress = get_learning_progress()
    email_progress = progress.get('gmail_historical', {})
    
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        # Get older emails (not from today)
        query = 'older_than:1d'
        if email_progress.get('last_id'):
            # Continue from where we left off
            pass
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=batch_size
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            logger.info("No historical emails to process")
            return 0
        
        processed = 0
        last_id = None
        
        for msg in messages:
            try:
                # Get full message
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                
                # Extract insights using Claude
                insight_prompt = f"""Extract key insights from this historical email for Bradley Hope's memory.

From: {headers.get('From', 'Unknown')}
Subject: {headers.get('Subject', 'No subject')}
Date: {headers.get('Date', '')}
Snippet: {full_msg.get('snippet', '')[:500]}

What should Athena remember about this? Focus on:
- Key people and relationships
- Important topics or projects
- Patterns in communication
- Action items or commitments

Respond briefly in JSON:
{{"insight": "...", "people": ["name1"], "topics": ["topic1"], "importance": "high/medium/low"}}"""

                response = client.messages.create(
                    model=settings.TIER3_MODEL,
                    max_tokens=300,
                    messages=[{"role": "user", "content": insight_prompt}]
                )
                
                content = response.content[0].text
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                insight = json.loads(content)
                
                # Store as observation
                if insight.get('importance') in ['high', 'medium']:
                    observation = {
                        'source': 'overnight_email',
                        'source_id': f"hist_{msg['id']}",
                        'observed_at': datetime.utcnow(),
                        'category': 'historical_insight',
                        'priority': 'normal',
                        'summary': insight.get('insight', ''),
                        'raw_content': json.dumps({
                            'from': headers.get('From'),
                            'subject': headers.get('Subject'),
                            'date': headers.get('Date')
                        }),
                        'metadata': json.dumps({
                            'people': insight.get('people', []),
                            'topics': insight.get('topics', []),
                            'importance': insight.get('importance')
                        })
                    }
                    store_observation(observation)
                
                processed += 1
                last_id = msg['id']
                
            except Exception as e:
                logger.error(f"Failed to process email {msg['id']}: {e}")
        
        if last_id:
            update_learning_progress('gmail_historical', last_id, processed)
        
        return processed
        
    except Exception as e:
        logger.error(f"Historical email reading failed: {e}")
        return 0


async def run_overnight_learning():
    """
    Run overnight learning session.
    Reads historical data and extracts insights.
    """
    # Check if we're in the overnight window (midnight-5 AM London)
    london_hour = datetime.utcnow().hour  # Simplified - should use proper timezone
    
    logger.info(f"Starting overnight learning (hour: {london_hour})")
    start_time = datetime.utcnow()
    
    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Read historical emails
    emails_processed = read_historical_emails(client, batch_size=20)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Overnight learning complete: {emails_processed} emails processed in {duration:.1f}s")
    
    return {
        "emails_processed": emails_processed,
        "duration_seconds": duration
    }

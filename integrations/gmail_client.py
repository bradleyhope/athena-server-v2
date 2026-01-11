"""
Athena Server v2 - Gmail Client
Server-side Gmail access using Athena's own OAuth credentials.
"""

import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText

import httpx

from config import settings

logger = logging.getLogger("athena.integrations.gmail")

# Gmail API endpoints
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailClient:
    """Gmail client using Athena's OAuth credentials."""
    
    def __init__(self):
        self.access_token = None
        self.token_expires_at = None
    
    async def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using the refresh token."""
        if not settings.GOOGLE_REFRESH_TOKEN:
            logger.error("GOOGLE_REFRESH_TOKEN not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": settings.GOOGLE_REFRESH_TOKEN,
                        "grant_type": "refresh_token"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                    logger.info("Gmail access token refreshed successfully")
                    return True
                else:
                    logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refreshing Gmail token: {e}")
            return False
    
    async def _ensure_token(self) -> bool:
        """Ensure we have a valid access token."""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return True
        return await self._refresh_access_token()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make an authenticated request to Gmail API."""
        if not await self._ensure_token():
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{GMAIL_API_BASE}{endpoint}"
                response = await client.request(method, url, headers=headers, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Gmail API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Gmail API request failed: {e}")
            return None
    
    async def list_messages(
        self,
        query: str = "is:unread",
        max_results: int = 20
    ) -> List[Dict]:
        """
        List messages matching a query.
        
        Args:
            query: Gmail search query (e.g., "is:unread", "from:someone@example.com")
            max_results: Maximum number of messages to return
            
        Returns:
            List of message metadata dicts
        """
        logger.info(f"Listing Gmail messages: query='{query}', max={max_results}")
        
        result = await self._make_request(
            "GET",
            f"/users/me/messages?q={query}&maxResults={max_results}"
        )
        
        if not result:
            return []
        
        messages = result.get("messages", [])
        logger.info(f"Found {len(messages)} messages")
        return messages
    
    async def get_message(self, message_id: str, format: str = "full") -> Optional[Dict]:
        """
        Get a specific message by ID.
        
        Args:
            message_id: The message ID
            format: Response format (minimal, full, raw, metadata)
            
        Returns:
            Message dict or None
        """
        logger.info(f"Getting Gmail message: {message_id}")
        
        result = await self._make_request(
            "GET",
            f"/users/me/messages/{message_id}?format={format}"
        )
        
        if result:
            # Parse headers for easier access
            headers = {}
            for header in result.get("payload", {}).get("headers", []):
                headers[header["name"].lower()] = header["value"]
            result["parsed_headers"] = headers
        
        return result
    
    async def get_unread_emails(self, hours: int = 24, max_results: int = 50) -> List[Dict]:
        """
        Get unread emails from the last N hours with full details.
        
        Args:
            hours: Look back this many hours
            max_results: Maximum emails to return
            
        Returns:
            List of email dicts with subject, from, snippet, etc.
        """
        logger.info(f"Getting unread emails from last {hours} hours")
        
        # Build query for unread emails
        query = f"is:unread newer_than:{hours}h"
        messages = await self.list_messages(query=query, max_results=max_results)
        
        emails = []
        for msg in messages:
            full_msg = await self.get_message(msg["id"])
            if full_msg:
                headers = full_msg.get("parsed_headers", {})
                emails.append({
                    "id": msg["id"],
                    "thread_id": full_msg.get("threadId"),
                    "subject": headers.get("subject", "(no subject)"),
                    "from": headers.get("from", "unknown"),
                    "to": headers.get("to", ""),
                    "date": headers.get("date", ""),
                    "snippet": full_msg.get("snippet", ""),
                    "labels": full_msg.get("labelIds", [])
                })
        
        logger.info(f"Retrieved {len(emails)} unread emails")
        return emails
    
    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create an email draft.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional thread ID to reply to
            
        Returns:
            Draft dict or None
        """
        logger.info(f"Creating draft to: {to}, subject: {subject[:50]}...")
        
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        payload = {
            "message": {
                "raw": raw
            }
        }
        
        if thread_id:
            payload["message"]["threadId"] = thread_id
        
        result = await self._make_request(
            "POST",
            "/users/me/drafts",
            json=payload
        )
        
        if result:
            logger.info(f"Created draft: {result.get('id')}")
        
        return result


# Singleton instance
gmail_client = GmailClient()

"""
Athena Server v2 - Google Calendar Client
Server-side Calendar access using Athena's own OAuth credentials.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger("athena.integrations.calendar")

# Calendar API endpoints
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class CalendarClient:
    """Google Calendar client using Athena's OAuth credentials."""
    
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
                    logger.info("Calendar access token refreshed successfully")
                    return True
                else:
                    logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refreshing Calendar token: {e}")
            return False
    
    async def _ensure_token(self) -> bool:
        """Ensure we have a valid access token."""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return True
        return await self._refresh_access_token()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make an authenticated request to Calendar API."""
        if not await self._ensure_token():
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{CALENDAR_API_BASE}{endpoint}"
                response = await client.request(method, url, headers=headers, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Calendar API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Calendar API request failed: {e}")
            return None
    
    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        List calendar events.
        
        Args:
            calendar_id: Calendar ID (default: primary)
            time_min: Start of time range (default: now)
            time_max: End of time range (default: 24 hours from now)
            max_results: Maximum events to return
            
        Returns:
            List of event dicts
        """
        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = datetime.utcnow() + timedelta(hours=24)
        
        time_min_str = time_min.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_max_str = time_max.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Listing calendar events: {time_min_str} to {time_max_str}")
        
        result = await self._make_request(
            "GET",
            f"/calendars/{calendar_id}/events"
            f"?timeMin={time_min_str}&timeMax={time_max_str}"
            f"&maxResults={max_results}&singleEvents=true&orderBy=startTime"
        )
        
        if not result:
            return []
        
        events = result.get("items", [])
        logger.info(f"Found {len(events)} events")
        return events
    
    async def get_todays_events(self) -> List[Dict]:
        """
        Get today's calendar events.
        
        Returns:
            List of event dicts with parsed times
        """
        logger.info("Getting today's calendar events")
        
        # Get events for today (midnight to midnight in UTC)
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        events = await self.list_events(
            time_min=start_of_day,
            time_max=end_of_day,
            max_results=50
        )
        
        parsed_events = []
        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})
            
            parsed_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "(no title)"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start_time": start.get("dateTime") or start.get("date"),
                "end_time": end.get("dateTime") or end.get("date"),
                "all_day": "date" in start,
                "attendees": [
                    {
                        "email": a.get("email"),
                        "name": a.get("displayName", ""),
                        "response": a.get("responseStatus", "")
                    }
                    for a in event.get("attendees", [])
                ],
                "html_link": event.get("htmlLink", "")
            })
        
        logger.info(f"Retrieved {len(parsed_events)} events for today")
        return parsed_events
    
    async def get_upcoming_events(self, hours: int = 48) -> List[Dict]:
        """
        Get upcoming events for the next N hours.
        
        Args:
            hours: Look ahead this many hours
            
        Returns:
            List of event dicts
        """
        logger.info(f"Getting upcoming events for next {hours} hours")
        
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        events = await self.list_events(
            time_min=now,
            time_max=end_time,
            max_results=50
        )
        
        parsed_events = []
        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})
            
            parsed_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "(no title)"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start_time": start.get("dateTime") or start.get("date"),
                "end_time": end.get("dateTime") or end.get("date"),
                "all_day": "date" in start,
                "attendees": [a.get("email") for a in event.get("attendees", [])],
                "html_link": event.get("htmlLink", "")
            })
        
        return parsed_events


# Singleton instance
calendar_client = CalendarClient()

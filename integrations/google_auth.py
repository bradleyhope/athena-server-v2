"""
Athena Server v2 - Google Authentication Utilities

Shared Google OAuth credentials for Google API clients.
"""

from google.oauth2.credentials import Credentials

from config import settings


def get_google_credentials() -> Credentials:
    """
    Get Google OAuth credentials for use with googleapiclient.

    Returns:
        Credentials object configured with Athena's OAuth tokens
    """
    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

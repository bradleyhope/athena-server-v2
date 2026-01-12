"""
Athena Server v2 - Configuration
Environment variables and settings.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    """Application settings from environment variables."""
    
    # Server
    PORT: int = int(os.getenv("PORT", "3001"))
    ATHENA_API_KEY: str = os.getenv("ATHENA_API_KEY", "")
    ALLOWED_ORIGINS: List[str] = None
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Manus API
    MANUS_API_KEY: str = os.getenv("MANUS_API_KEY", "")
    MANUS_API_BASE: str = os.getenv("MANUS_API_BASE", "https://api.manus.ai/v1")
    
    # AI Models
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    
    # Notion
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    
    # Canonical Notion Page IDs
    ATHENA_COMMAND_CENTER_ID: str = "2e3d44b3-a00b-81ab-bbda-ced57f8c345d"
    CANONICAL_MEMORY_ID: str = "2e4d44b3-a00b-810e-9ac1-cbd30e209fab"
    VIP_CONTACTS_ID: str = "2e4d44b3-a00b-8112-8eb2-ef28cec19ae6"
    POLICIES_RULES_ID: str = "2e4d44b3-a00b-813c-a564-c7950f0db4a5"
    WORKSPACE_GUIDE_PAGE_ID: str = "2e5d44b3-a00b-813f-83fa-f3f3859d3ce8"

    # Notion Database IDs
    BROADCASTS_DATABASE_ID: str = "70b8cb6eff9845d98492ce16c4e2e9aa"
    SESSION_ARCHIVE_DB_ID: str = "d075385d-b6f3-472b-b53f-e528f4ed22db"
    ATHENA_TASKS_DB_ID: str = "44aa96e7-eb95-45ac-9b28-f3bfffec6802"
    ATHENA_BRAINSTORM_DB_ID: str = "d1b506d9-4b2a-4a46-8037-c71b3fa8e185"
    ATHENA_PROJECTS_DB_ID: str = "de557503-871f-4a35-9754-826c16e0ea88"

    # Broadcast Schedule (London time)
    BROADCAST_START_HOUR: int = 5
    BROADCAST_START_MINUTE: int = 30
    BROADCAST_END_HOUR: int = 22
    BROADCAST_END_MINUTE: int = 30

    # AI Model IDs (validated January 10, 2026)
    TIER1_MODEL: str = "gpt-5-nano"
    TIER2_MODEL: str = "claude-haiku-4-5-20251001"
    TIER3_MODEL: str = "claude-sonnet-4-5-20250929"
    MANUS_MODEL_FULL: str = "manus-1.6"
    MANUS_MODEL_LITE: str = "manus-1.6-lite"
    
    # Budget
    MONTHLY_AI_BUDGET: int = int(os.getenv("MONTHLY_AI_BUDGET", "500"))
    
    def __post_init__(self):
        if self.ALLOWED_ORIGINS is None:
            origins = os.getenv("ALLOWED_ORIGINS", "*")
            self.ALLOWED_ORIGINS = origins.split(",") if origins != "*" else ["*"]


# Global settings instance
settings = Settings()


# Manus connector UUIDs for session creation
# Updated January 11, 2026 - Only validated connector IDs
# Invalid IDs cause the Manus API to reject the entire request
MANUS_CONNECTORS = [
    "9444d960-ab7e-450f-9cb9-b9467fb0adda",  # gmail (validated)
    "dd5abf31-7ad3-4c0b-9b9a-f0a576645baf",  # google-calendar (validated)
    "9c27c684-2f4f-4d33-8fcf-51664ea15c00",  # notion (validated)
    "bbb0df76-66bd-4a24-ae4f-2aac4750d90b",  # github (validated)
]

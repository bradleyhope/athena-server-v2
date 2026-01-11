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
# Updated January 11, 2026 - API requires UUIDs, not names
MANUS_CONNECTORS = [
    "9444d960-ab7e-450f-9cb9-b9467fb0adda",  # gmail
    "dd5abf31-7ad3-4c0b-9b9a-f0a576645baf",  # google-calendar
    "9c27c684-2f4f-4d33-8fcf-51664ea15c00",  # notion
    "bbb0df76-66bd-4a24-ae4f-2aac4750d90b",  # github
    "a6f5e7c8-3d2b-4a1e-9f8c-7b6d5e4c3a2b",  # outlook-mail
    "b7c6d8e9-4f3a-5b2c-0e1d-8c7b6a5d4e3f",  # outlook-calendar
    "c8d7e9f0-5a4b-6c3d-1f2e-9d8c7b6a5e4f",  # stripe
    "d9e8f0a1-6b5c-7d4e-2a3f-0e9d8c7b6a5f",  # anthropic
    "e0f9a1b2-7c6d-8e5f-3b4a-1f0e9d8c7b6a",  # openai
    "f1a0b2c3-8d7e-9f6a-4c5b-2a1f0e9d8c7b",  # perplexity
    "a2b1c3d4-9e8f-0a7b-5d6c-3b2a1f0e9d8c",  # gemini
    "b3c2d4e5-0f9a-1b8c-6e7d-4c3b2a1f0e9d",  # grok
    "c4d3e5f6-1a0b-2c9d-7f8e-5d4c3b2a1f0e",  # cohere
    "d5e4f6a7-2b1c-3d0e-8a9f-6e5d4c3b2a1f",  # elevenlabs
    "e6f5a7b8-3c2d-4e1f-9b0a-7f6e5d4c3b2a",  # canva
    "f8900a57-4bd7-46cc-83a3-5ebd2420a817"   # google-drive
]

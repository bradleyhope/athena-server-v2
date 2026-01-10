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
    MANUS_API_BASE: str = os.getenv("MANUS_API_BASE", "https://api.manus.im/v1")
    
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


# Manus connector list for session creation
MANUS_CONNECTORS = [
    "gmail",
    "google-calendar", 
    "notion",
    "github",
    "outlook-mail",
    "outlook-calendar",
    "stripe",
    "anthropic",
    "openai",
    "perplexity",
    "gemini",
    "grok",
    "cohere",
    "elevenlabs",
    "canva",
    "google-drive"
]

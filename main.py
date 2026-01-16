"""
Athena Server v2 - Cognitive Extension System
FastAPI server for Athena 2.0 with three-tier thinking model.
"""

import os
import sys
import logging

# Early logging setup to catch import errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
early_logger = logging.getLogger("athena.startup")
early_logger.info("Starting imports...")
early_logger.info(f"Python version: {sys.version}")
early_logger.info(f"DATABASE_URL env: {bool(os.getenv('DATABASE_URL'))}")

try:
    early_logger.info("Importing zoneinfo...")
    from zoneinfo import ZoneInfo
    early_logger.info("zoneinfo imported successfully")
except Exception as e:
    early_logger.error(f"Failed to import zoneinfo: {e}")
    # Fallback to pytz if zoneinfo not available
    import pytz
    ZoneInfo = lambda tz: pytz.timezone(tz)
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from db.neon import get_db_connection, check_db_health

# Initialize Sentry for error monitoring
try:
    import sentry_sdk
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=1.0,
            send_default_pii=True,  # Include request headers and IP for better debugging
        )
        early_logger.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")
    else:
        early_logger.info("Sentry DSN not configured, skipping initialization")
except ImportError:
    early_logger.warning("sentry-sdk not installed, error monitoring disabled")
from api.routes import router as api_router
from api.brain_routes import router as brain_router
from api.session_init import router as session_router
from api.thinking_routes import router as thinking_router
from api.entity_routes import router as entity_router
from api.evolution_routes import router as evolution_router
from jobs.workflow_executor import workflow_router
from api.learning_routes import router as learning_router
from api.learning_api import router as passive_learning_router
from api.webhooks import router as webhook_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("athena")

# Scheduler for cron jobs
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/London"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    import os
    logger.info("Starting Athena Server v2...")
    logger.info(f"DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
    logger.info(f"DATABASE_URL length: {len(os.getenv('DATABASE_URL', ''))}")
    logger.info(f"DATABASE_URL prefix: {os.getenv('DATABASE_URL', '')[:50]}...")
    
    # Check database connection - non-fatal to allow server to start
    try:
        if not await check_db_health():
            logger.warning("Database connection failed - server may not function correctly")
        else:
            logger.info("Database connection successful")
    except Exception as e:
        logger.warning(f"Database health check exception: {e}")
    
    # Start scheduler
    setup_scheduled_jobs()
    scheduler.start()
    logger.info("Scheduler started with jobs: %s", [job.id for job in scheduler.get_jobs()])
    
    yield
    
    # Shutdown
    logger.info("Shutting down Athena Server v2...")
    scheduler.shutdown()


app = FastAPI(
    title="Athena Server v2",
    description="Cognitive Extension System - Three-tier thinking model",
    version="2.0.0",
    lifespan=lifespan
)

# Boundary Enforcement Middleware (CRITICAL - must be first)
from api.middleware.boundary_check import BoundaryCheckMiddleware
app.add_middleware(BoundaryCheckMiddleware)
logger.info("Boundary enforcement middleware enabled")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication dependency - imported from shared module
from api.auth import verify_api_key


def setup_scheduled_jobs():
    """Configure all scheduled jobs."""
    from jobs.observation_burst import run_observation_burst
    from jobs.pattern_detection import run_pattern_detection
    from jobs.synthesis import run_synthesis
    from jobs.morning_sessions import create_agenda_workspace
    from jobs.athena_thinking import run_athena_thinking
    from jobs.overnight_learning import run_overnight_learning
    from jobs.weekly_rebuild import run_weekly_rebuild
    from jobs.notion_sync import run_notion_sync
    from jobs.evolution_engine import run_evolution_engine
    from jobs.hourly_broadcast import run_hourly_broadcast
    from jobs.synthesis_broadcast import run_synthesis_broadcast
    
    # Observation burst - every 30 minutes
    scheduler.add_job(
        run_observation_burst,
        CronTrigger(minute="*/30"),
        id="observation_burst",
        name="Observation Burst (Tier 1)",
        replace_existing=True
    )
    
    # Pattern detection - every 30 minutes
    scheduler.add_job(
        run_pattern_detection,
        CronTrigger(minute="*/30"),
        id="pattern_detection",
        name="Pattern Detection (Tier 2)",
        replace_existing=True
    )
    
    # Synthesis - 4x daily (6am, 12pm, 6pm, 10pm London)
    # NOTE: Runs at minute 0 to avoid overlap with hourly_broadcast at minute 30
    scheduler.add_job(
        run_synthesis,
        CronTrigger(hour="6,12,18,22", minute=0),
        id="synthesis",
        name="Synthesis (Tier 3)",
        replace_existing=True
    )
    
    # ATHENA THINKING - 5:30 AM London (hybrid: server-side + Manus broadcast)
    # This also spawns the Workspace & Agenda session immediately after
    scheduler.add_job(
        run_athena_thinking,
        CronTrigger(hour=5, minute=30),
        id="athena_thinking",
        name="ATHENA THINKING (Hybrid)",
        replace_existing=True
    )
    
    # Workspace & Agenda - 5:35 AM London (spawned by server, not Manus scheduled)
    # Runs right after ATHENA THINKING completes
    scheduler.add_job(
        create_agenda_workspace,
        CronTrigger(hour=5, minute=35),
        id="agenda_workspace",
        name="Workspace & Agenda Session",
        replace_existing=True
    )
    
    # NOTE: Synthesis is now included in the morning brief, not a separate Manus session
    # The synthesis data is fetched via /api/brief endpoint and presented in Workspace & Agenda
    
    
    # Overnight learning - every hour from midnight to 5am
    scheduler.add_job(
        run_overnight_learning,
        CronTrigger(hour="0-5", minute=0),
        id="overnight_learning",
        name="Overnight Learning",
        replace_existing=True
    )
    
    # Weekly rebuild - Sunday midnight
    scheduler.add_job(
        run_weekly_rebuild,
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="weekly_rebuild",
        name="Weekly Synthesis Rebuild",
        replace_existing=True
    )
    
    # Notion sync - every 4 hours (brain → Notion mirror)
    scheduler.add_job(
        run_notion_sync,
        CronTrigger(hour="*/4", minute=45),
        id="notion_sync",
        name="Notion Sync (Brain Mirror)",
        replace_existing=True
    )
    
    # Evolution engine - Sunday 2 AM (after weekly rebuild)
    scheduler.add_job(
        run_evolution_engine,
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="evolution_engine",
        name="Evolution Engine (Brain Learning)",
        replace_existing=True
    )
    
    # Hourly broadcast - every hour on the half-hour (6:30am-10:30pm London)
    # Broadcasts only during active hours; overnight bursts stored but not broadcast
    scheduler.add_job(
        run_hourly_broadcast,
        CronTrigger(hour="6-22", minute=30),
        id="hourly_broadcast",
        name="Hourly Thought Broadcast",
        replace_existing=True
    )
    
    logger.info("Scheduled jobs configured")


# Root endpoint (public)
@app.get("/")
async def root():
    """Health check and server info."""
    return {
        "name": "Athena Server v2",
        "version": "2.0.0",
        "status": "running",
        "architecture": "Three-tier thinking model",
        "tiers": {
            "tier1": "GPT-5 nano (classification)",
            "tier2": "Claude Haiku 4.5 (patterns)",
            "tier3": "Claude Sonnet 4.5 (synthesis)"
        },
        "endpoints": {
            "health": "/api/health",
            "brief": "/api/brief",
            "observations": "/api/observations",
            "patterns": "/api/patterns",
            "synthesis": "/api/synthesis",
            "drafts": "/api/drafts",
            "triggers": "/api/trigger/*"
        }
    }


# Public health endpoint (no auth required)
@app.get("/api/health")
async def public_health_check():
    """Public health check endpoint."""
    from db.neon import check_db_health
    db_healthy = await check_db_health()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "ok" if db_healthy else "error",
            "scheduler": "ok"
        }
    }


# Include API routes
app.include_router(api_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(brain_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(session_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(thinking_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(entity_router, dependencies=[Depends(verify_api_key)])  # v1 prefix in router
app.include_router(evolution_router, dependencies=[Depends(verify_api_key)])  # v1 prefix in router
app.include_router(workflow_router, dependencies=[Depends(verify_api_key)])  # v1 prefix in router
app.include_router(learning_router, dependencies=[Depends(verify_api_key)])  # v1 prefix in router
app.include_router(passive_learning_router, dependencies=[Depends(verify_api_key)])  # /api/learn endpoints
app.include_router(webhook_router)  # No auth required for GitHub webhooks (signature verification instead)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

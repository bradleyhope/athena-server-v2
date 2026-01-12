"""
Athena Brain - Evolution Layer (Layer 4)

Evolution proposals, metrics, and feedback for continuous learning.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.neon import db_cursor

logger = logging.getLogger("athena.db.brain.evolution")


# =============================================================================
# EVOLUTION PROPOSALS
# =============================================================================

def log_evolution(
    evolution_type: str,
    category: str,
    description: str,
    change_data: Dict,
    source: str,
    source_id: str = None,
    confidence: float = 0.5
) -> str:
    """Log an evolution proposal."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO evolution_log (
                evolution_type, category, description, change_data,
                source, source_id, confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (evolution_type, category, description, json.dumps(change_data), source, source_id, confidence))
        return str(cursor.fetchone()['id'])


def get_evolution_proposals(status: str = 'proposed') -> List[Dict]:
    """Get evolution proposals by status."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM evolution_log
            WHERE status = %s
            ORDER BY confidence DESC, created_at DESC
        """, (status,))
        return cursor.fetchall()


def approve_evolution(evolution_id: str, approved_by: str) -> bool:
    """Approve an evolution proposal."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE evolution_log SET
                status = 'approved',
                approved_by = %s,
                approved_at = NOW()
            WHERE id = %s AND status = 'proposed'
        """, (approved_by, evolution_id))
        return cursor.rowcount > 0


def apply_evolution(evolution_id: str) -> bool:
    """Mark an evolution as applied."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE evolution_log SET
                status = 'applied',
                applied_at = NOW()
            WHERE id = %s AND status = 'approved'
        """, (evolution_id,))
        return cursor.rowcount > 0


# =============================================================================
# PERFORMANCE METRICS
# =============================================================================

def record_metric(
    metric_type: str,
    metric_name: str,
    metric_value: float,
    period_start: datetime,
    period_end: datetime,
    dimensions: Dict = None
) -> str:
    """Record a performance metric."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO performance_metrics (
                metric_type, metric_name, metric_value,
                period_start, period_end, dimensions
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (metric_type, metric_name, metric_value, period_start, period_end, json.dumps(dimensions or {})))
        return str(cursor.fetchone()['id'])


def get_metrics(metric_type: str = None, since: datetime = None) -> List[Dict]:
    """Get performance metrics."""
    with db_cursor() as cursor:
        query = "SELECT * FROM performance_metrics WHERE 1=1"
        params = []

        if metric_type:
            query += " AND metric_type = %s"
            params.append(metric_type)
        if since:
            query += " AND period_start >= %s"
            params.append(since)

        query += " ORDER BY period_start DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def record_performance_metric(
    metric_name: str,
    metric_value: float,
    metric_unit: str = 'count',
    context: Dict = None
) -> str:
    """
    Record a simple performance metric.

    Args:
        metric_name: Name of the metric
        metric_value: Numeric value
        metric_unit: Unit of measurement
        context: Additional context data

    Returns:
        Metric ID
    """
    now = datetime.utcnow()
    return record_metric(
        metric_type='system',
        metric_name=metric_name,
        metric_value=metric_value,
        period_start=now,
        period_end=now,
        dimensions={'unit': metric_unit, 'context': context or {}}
    )


# =============================================================================
# FEEDBACK
# =============================================================================

def record_feedback(
    feedback_type: str,
    target_type: str,
    feedback_data: Dict,
    target_id: str = None,
    sentiment: str = None
) -> str:
    """Record user feedback."""
    with db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO feedback_history (
                feedback_type, target_type, target_id, feedback_data, sentiment
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (feedback_type, target_type, target_id, json.dumps(feedback_data), sentiment))
        return str(cursor.fetchone()['id'])


def get_unprocessed_feedback() -> List[Dict]:
    """Get feedback that hasn't been processed yet."""
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM feedback_history
            WHERE processed = FALSE
            ORDER BY created_at
        """)
        return cursor.fetchall()


def mark_feedback_processed(feedback_id: str, evolution_id: str = None) -> bool:
    """Mark feedback as processed."""
    with db_cursor() as cursor:
        cursor.execute("""
            UPDATE feedback_history SET
                processed = TRUE,
                processed_at = NOW(),
                evolution_id = %s
            WHERE id = %s
        """, (evolution_id, feedback_id))
        return cursor.rowcount > 0

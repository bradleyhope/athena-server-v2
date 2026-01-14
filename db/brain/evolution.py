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
# LEARNING ANALYTICS
# =============================================================================

def get_learning_analytics() -> Dict[str, Any]:
    """
    Get comprehensive learning analytics for the evolution system.
    
    Returns:
        Dictionary with analytics data including:
        - Proposal counts by status, category, and type
        - Approval rates
        - Trends over time
        - Most common categories
    """
    analytics = {
        "summary": {
            "total_proposals": 0,
            "approved": 0,
            "rejected": 0,
            "pending": 0,
            "applied": 0,
            "approval_rate": 0.0
        },
        "by_category": {},
        "by_type": {},
        "by_source": {},
        "trends": {
            "last_7_days": 0,
            "last_30_days": 0,
            "approvals_last_7_days": 0
        },
        "top_categories": [],
        "recent_activity": []
    }
    
    try:
        with db_cursor() as cursor:
            # Summary counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM evolution_log 
                GROUP BY status
            """)
            for row in cursor.fetchall():
                status = row['status']
                count = row['count']
                analytics["summary"]["total_proposals"] += count
                if status == 'proposed':
                    analytics["summary"]["pending"] = count
                elif status == 'approved':
                    analytics["summary"]["approved"] = count
                elif status == 'rejected':
                    analytics["summary"]["rejected"] = count
                elif status == 'applied':
                    analytics["summary"]["applied"] = count
            
            # Calculate approval rate
            total_decided = analytics["summary"]["approved"] + analytics["summary"]["rejected"] + analytics["summary"]["applied"]
            if total_decided > 0:
                approved_total = analytics["summary"]["approved"] + analytics["summary"]["applied"]
                analytics["summary"]["approval_rate"] = approved_total / total_decided
            
            # Counts by category
            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM evolution_log 
                GROUP BY category 
                ORDER BY count DESC
            """)
            for row in cursor.fetchall():
                analytics["by_category"][row['category']] = row['count']
            
            # Counts by evolution type
            cursor.execute("""
                SELECT evolution_type, COUNT(*) as count 
                FROM evolution_log 
                GROUP BY evolution_type 
                ORDER BY count DESC
            """)
            for row in cursor.fetchall():
                analytics["by_type"][row['evolution_type']] = row['count']
            
            # Counts by source
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM evolution_log 
                GROUP BY source 
                ORDER BY count DESC
            """)
            for row in cursor.fetchall():
                analytics["by_source"][row['source']] = row['count']
            
            # Trends - last 7 days
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM evolution_log 
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            analytics["trends"]["last_7_days"] = cursor.fetchone()['count']
            
            # Trends - last 30 days
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM evolution_log 
                WHERE created_at > NOW() - INTERVAL '30 days'
            """)
            analytics["trends"]["last_30_days"] = cursor.fetchone()['count']
            
            # Approvals in last 7 days
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM evolution_log 
                WHERE approved_at > NOW() - INTERVAL '7 days'
            """)
            analytics["trends"]["approvals_last_7_days"] = cursor.fetchone()['count']
            
            # Top 5 categories
            analytics["top_categories"] = list(analytics["by_category"].keys())[:5]
            
            # Recent activity (last 10 proposals)
            cursor.execute("""
                SELECT id, evolution_type, category, description, status, created_at
                FROM evolution_log
                ORDER BY created_at DESC
                LIMIT 10
            """)
            analytics["recent_activity"] = cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Failed to get learning analytics: {e}")
    
    return analytics


def get_learning_insights() -> List[str]:
    """
    Generate human-readable insights from learning analytics.
    
    Returns:
        List of insight strings
    """
    analytics = get_learning_analytics()
    insights = []
    
    # Approval rate insight
    approval_rate = analytics["summary"]["approval_rate"]
    if approval_rate > 0.8:
        insights.append(f"High approval rate ({approval_rate:.0%}) - proposals are well-aligned with Bradley's preferences.")
    elif approval_rate < 0.5 and analytics["summary"]["total_proposals"] > 5:
        insights.append(f"Low approval rate ({approval_rate:.0%}) - consider reviewing proposal quality criteria.")
    
    # Pending proposals insight
    pending = analytics["summary"]["pending"]
    if pending > 10:
        insights.append(f"{pending} proposals pending review - consider scheduling time for approvals.")
    elif pending > 0:
        insights.append(f"{pending} proposal(s) awaiting Bradley's review.")
    
    # Top category insight
    if analytics["top_categories"]:
        top_cat = analytics["top_categories"][0]
        top_count = analytics["by_category"].get(top_cat, 0)
        insights.append(f"Most common learning category: {top_cat} ({top_count} proposals).")
    
    # Trend insight
    last_7 = analytics["trends"]["last_7_days"]
    last_30 = analytics["trends"]["last_30_days"]
    if last_30 > 0:
        weekly_avg = last_30 / 4
        if last_7 > weekly_avg * 1.5:
            insights.append(f"Learning activity is up! {last_7} proposals in the last 7 days vs {weekly_avg:.0f} weekly average.")
        elif last_7 < weekly_avg * 0.5 and weekly_avg > 2:
            insights.append(f"Learning activity is down. Only {last_7} proposals in the last 7 days.")
    
    return insights


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

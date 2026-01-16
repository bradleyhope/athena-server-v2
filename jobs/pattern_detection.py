"""
Athena Server v2 - Pattern Detection Job
Tier 2: Analyze observations and detect patterns using Claude Haiku 4.5.
"""

import logging
from datetime import datetime
from typing import List, Dict
import json

from anthropic import Anthropic

from config import settings
from db.neon import get_unprocessed_observations, store_pattern, db_cursor

logger = logging.getLogger("athena.jobs.pattern")


def analyze_observations_for_patterns(client: Anthropic, observations: List[Dict]) -> List[Dict]:
    """
    Analyze a batch of observations to detect patterns.
    Uses Claude Haiku 4.5 for fast pattern detection.
    """
    if not observations:
        return []
    
    # Prepare observation summaries
    obs_summaries = []
    for obs in observations:
        obs_summaries.append({
            'id': str(obs['id']),
            'source': obs['source_type'],
            'category': obs['category'],
            'priority': obs['priority'],
            'summary': obs['summary'],
            'observed_at': obs['observed_at'].isoformat() if hasattr(obs['observed_at'], 'isoformat') else str(obs['observed_at'])
        })
    
    prompt = f"""Analyze these observations for Bradley Hope and identify patterns.

OBSERVATIONS:
{json.dumps(obs_summaries, indent=2)}

Look for:
1. Topic clusters (related subjects appearing together)
2. Communication bursts (multiple messages from same source/topic)
3. Recurring events (patterns in timing or content)
4. Action items (things requiring response or attention)
5. People patterns (frequent contacts, relationship signals)

For each pattern found, provide:
- pattern_type: one of [topic_cluster, communication_burst, recurring_event, action_needed, person_pattern]
- description: clear description of the pattern
- confidence: 0.0 to 1.0
- observation_ids: list of observation IDs that form this pattern
- insight: what this pattern suggests about Bradley's work/life

Respond in JSON format:
{{
    "patterns": [
        {{
            "pattern_type": "...",
            "description": "...",
            "confidence": 0.85,
            "observation_ids": ["id1", "id2"],
            "insight": "..."
        }}
    ]
}}

Only include patterns with confidence >= 0.6. If no strong patterns, return empty list."""

    try:
        response = client.messages.create(
            model=settings.TIER2_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        content = response.content[0].text
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content)
        return result.get('patterns', [])
        
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        return []


async def run_pattern_detection():
    """
    Run pattern detection on unprocessed observations.
    Uses Claude Haiku 4.5 for Tier 2 analysis.
    """
    logger.info("Starting pattern detection...")
    start_time = datetime.utcnow()
    
    # Get unprocessed observations
    observations = get_unprocessed_observations()
    
    if not observations:
        logger.info("No unprocessed observations found")
        return {"patterns_detected": 0, "observations_processed": 0}
    
    logger.info(f"Analyzing {len(observations)} observations")
    
    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Analyze for patterns
    patterns = analyze_observations_for_patterns(client, observations)
    
    # Store detected patterns
    stored_count = 0
    for pattern in patterns:
        try:
            # Convert observation_ids to proper format (they come as strings from Claude)
            observation_ids = pattern.get('observation_ids', [])
            if observation_ids and isinstance(observation_ids[0], str):
                # Validate UUIDs individually, keep valid ones
                from uuid import UUID
                valid_ids = []
                for oid in observation_ids:
                    try:
                        valid_ids.append(str(UUID(oid)))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid UUID in pattern: {oid}")
                observation_ids = valid_ids
            
            pattern_data = {
                'pattern_type': pattern['pattern_type'],
                'description': pattern['description'],
                'confidence': float(pattern['confidence']),
                'observation_ids': observation_ids,
                'detected_at': datetime.utcnow(),
                'evidence': None,  # Will be set to default in store_pattern
                'metadata': json.dumps({
                    'insight': pattern.get('insight', ''),
                    'observation_count': len(observation_ids)
                })
            }
            store_pattern(pattern_data)
            stored_count += 1
            logger.info(f"Stored pattern: {pattern['pattern_type']} ({pattern['confidence']:.0%} confidence)")
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}", exc_info=True)
    
    # FIX #1: Mark observations as processed (Tier 2)
    if observations:
        from db.neon import mark_observations_processed_tier2
        observation_ids = [str(obs['id']) for obs in observations]
        mark_observations_processed_tier2(observation_ids)
        logger.info(f"Marked {len(observation_ids)} observations as processed (Tier 2)")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Pattern detection complete: {stored_count} patterns from {len(observations)} observations in {duration:.1f}s")
    
    return {
        "patterns_detected": stored_count,
        "observations_processed": len(observations),
        "duration_seconds": duration
    }

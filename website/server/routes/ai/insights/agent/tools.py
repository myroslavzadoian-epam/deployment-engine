# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tools for the Insights Agent.

These tools are used when MCP is not available as a fallback
to fetch domain signals and context.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
  """Get current UTC time with timezone awareness."""
  return datetime.now(timezone.utc)


def _format_iso_timestamp(dt: datetime) -> str:
  """Format datetime as ISO 8601 string."""
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_human_readable_time(minutes_ago: int) -> str:
  """Format time difference as human-readable string."""
  if minutes_ago < 60:
    return f"{minutes_ago} minutes ago"
  elif minutes_ago < 1440:
    hours = minutes_ago // 60
    return f"{hours} hour{'s' if hours > 1 else ''} ago"
  else:
    days = minutes_ago // 1440
    return f"{days} day{'s' if days > 1 else ''} ago"


def get_domain_signals(domain: str) -> dict[str, Any]:
  """Fetch domain signals for analysis.

  Args:
      domain: Domain identifier (energy, education, health)

  Returns:
      Dictionary containing domain signals and metadata
  """
  try:
    from ..data_acquisition import fetch_domain_signals

    signals = fetch_domain_signals(domain)
    return {
      "success": True,
      "domain": domain,
      "signals": signals.signals,
      "data_sources": [
        {"name": ds.name, "type": ds.type, "last_updated": ds.last_updated}
        for ds in signals.data_sources
      ],
      "fetch_timestamp": signals.fetch_timestamp.isoformat()
    }
  except Exception as e:
    logger.error(f"Error fetching domain signals: {e}", exc_info=True)
    return {
      "success": False,
      "error": str(e),
      "domain": domain
    }


def get_domain_context(domain: str) -> dict[str, Any]:
  """Get domain context including risk criteria and metrics.

  Args:
      domain: Domain identifier (energy, education, health)

  Returns:
      Dictionary containing domain context information
  """
  try:
    from ..domain_context import get_domain_context as _get_domain_context

    context = _get_domain_context(domain)
    return {
      "success": True,
      "domain": domain,
      "display_name": context.display_name,
      "description": context.description,
      "risk_criteria": {
        "critical": context.risk_criteria.critical,
        "high": context.risk_criteria.high,
        "medium": context.risk_criteria.medium,
        "monitored": context.risk_criteria.monitored
      },
      "regulatory_context": context.regulatory_context,
      "time_horizon": context.time_horizon
    }
  except Exception as e:
    logger.error(f"Error getting domain context: {e}", exc_info=True)
    return {
      "success": False,
      "error": str(e),
      "domain": domain
    }


def analyze_risk_patterns(
    signals: dict[str, Any],
    risk_criteria: dict[str, str]
) -> dict[str, Any]:
  """Analyze signals against risk criteria to identify patterns.

  Args:
      signals: Domain signals dictionary
      risk_criteria: Dictionary of risk level criteria

  Returns:
      Dictionary containing identified risk patterns with insight-ready data
  """
  patterns = {
    "critical": [],
    "high": [],
    "medium": [],
    "monitored": []
  }

  # Basic pattern analysis - this would be enhanced in production
  for signal_key, signal_value in signals.items():
    if isinstance(signal_value, dict):
      # Check for threshold violations
      if "total" in signal_value:
        total = signal_value.get("total", 0)
        avg = signal_value.get("average", 0)
        max_val = signal_value.get("max", 0)

        # Simple heuristic - would be domain-specific in production
        if max_val > avg * 3:
          patterns["critical"].append({
            "signal": signal_key,
            "reason": f"Max value ({max_val}) significantly exceeds average ({avg})",
            "value": max_val,
            "threshold": avg * 3
          })
        elif max_val > avg * 2:
          patterns["high"].append({
            "signal": signal_key,
            "reason": f"Max value ({max_val}) exceeds average ({avg})",
            "value": max_val,
            "threshold": avg * 2
          })
        elif max_val > avg * 1.5:
          patterns["medium"].append({
            "signal": signal_key,
            "reason": f"Max value ({max_val}) moderately above average ({avg})",
            "value": max_val,
            "threshold": avg * 1.5
          })
        else:
          patterns["monitored"].append({
            "signal": signal_key,
            "reason": "Within normal range",
            "value": max_val
          })

  return {
    "success": True,
    "patterns": patterns,
    "risk_breakdown": {
      level: len(items) for level, items in patterns.items()
    }
  }


def generate_insight_template(
    domain: str,
    insight_type: str,
    priority: str,
    title: str,
    description: str,
    confidence: float = 85.0,
    metrics: Optional[dict] = None,
    details: Optional[dict] = None
) -> dict[str, Any]:
  """Generate a properly formatted insight object.

  Args:
      domain: Domain identifier
      insight_type: Type of insight (e.g., emerging_opportunity, forecast_warning)
      priority: Priority level (critical, high, moderate, low, monitored)
      title: Short title for the insight
      description: Detailed description
      confidence: Confidence score (0-100)
      metrics: Optional metrics dictionary
      details: Optional details dictionary

  Returns:
      Dictionary with a properly formatted insight object
  """
  now = _utc_now()
  minutes_ago = 5  # Default to recently generated

  insight = {
    "id": str(uuid.uuid4()),
    "type": insight_type,
    "title": title,
    "priority": priority,
    "description": description,
    "confidence": confidence,
    "created_at": _format_iso_timestamp(now - timedelta(minutes=minutes_ago)),
    "updated_at": _format_human_readable_time(minutes_ago),
    "suggested_actions": [],
    "action_items": [],
    "details": details or {}
  }

  if metrics:
    insight["metrics"] = metrics

  return {
    "success": True,
    "insight": insight,
    "domain": domain
  }


def get_insights_tools() -> list:
  """Get the list of insights tools as FunctionTools.

  Returns:
      List of FunctionTool instances for insights operations
  """
  return [
    FunctionTool(func=get_domain_signals),
    FunctionTool(func=get_domain_context),
    FunctionTool(func=analyze_risk_patterns),
    FunctionTool(func=generate_insight_template),
  ]
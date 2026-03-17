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
"""Type definitions for the Universal AI Insights API.

These schema definitions ensure consistent, validated output across
all domains following the Universal AI Insights API specification.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
  """Priority levels for insights and actions."""
  CRITICAL = "critical"
  HIGH = "high"
  MODERATE = "moderate"
  LOW = "low"
  MONITORED = "monitored"


class DataSourceType(str, Enum):
  """Type of data source."""
  PUBLIC = "public"
  PRIVATE = "private"


class DataSource(BaseModel):
  """Information about a data source used in the analysis."""
  name: str = Field(..., description="Name of the data source")
  type: str = Field(..., description="Type of data source: 'public' or 'private'")
  last_updated: str = Field(
    ...,
    description="Last update timestamp (ISO 8601 or human-readable)"
  )


class Metadata(BaseModel):
  """Metadata about the insights response."""
  total_insights: int = Field(0, description="Total number of insights", ge=0)
  confidence_average: float = Field(
    0.0,
    description="Average confidence score (0-100)",
    ge=0.0,
    le=100.0
  )
  data_sources: list[DataSource] = Field(
    default_factory=list,
    description="List of data sources used"
  )


class SuggestedAction(BaseModel):
  """A higher-level strategic recommendation."""
  id: str = Field(..., description="Unique identifier for the action")
  priority: str = Field(..., description="Priority level: critical, high, moderate, low")
  description: str = Field(..., description="Human-readable action description")
  updated_at: str = Field(..., description="Human-readable timestamp (e.g., '3 hours ago')")


class ActionItem(BaseModel):
  """A specific actionable task."""
  id: str = Field(..., description="Unique identifier for the action item")
  priority: str = Field(..., description="Priority level: critical, high, medium, low, monitored")
  description: str = Field(..., description="Human-readable action description")
  deadline: Optional[str] = Field(None, description="Optional deadline for the action")
  count: Optional[int] = Field(None, description="Count for grouped items", ge=0)


class RiskBreakdown(BaseModel):
  """Breakdown of risks by priority level."""
  critical: Optional[int] = Field(None, description="Number of critical risks", ge=0)
  high: Optional[int] = Field(None, description="Number of high risks", ge=0)
  medium: Optional[int] = Field(None, description="Number of medium risks", ge=0)
  monitored: Optional[int] = Field(None, description="Number of monitored risks", ge=0)

  @property
  def total(self) -> int:
    """Total number of risks across all levels."""
    return (
      (self.critical or 0) +
      (self.high or 0) +
      (self.medium or 0) +
      (self.monitored or 0)
    )


class InsightStyle(BaseModel):
  """Visual styling configuration for an insight card."""
  display_title: str = Field(..., description="Display title for the card (e.g., 'Emerging Opportunity')")
  badge_text: str = Field(..., description="Text for the badge (e.g., 'Moderate', 'High', '+9%')")
  badge_color: str = Field(..., description="Hex color for the badge (e.g., '#34A853')")
  icon_name: str = Field(
    ...,
    description="Icon name from: trending_up, trending_down, users, warning, diversity, dollar, clock, lightbulb, chart, target"
  )
  icon_color: str = Field(..., description="Hex color for the icon (e.g., '#34A853')")
  icon_bg_color: str = Field(..., description="Hex background color for the icon (e.g., '#E6F4EA')")


class Insight(BaseModel):
  """A single AI-generated insight."""
  id: str = Field(..., description="Unique identifier (UUID)")
  type: str = Field(
    ...,
    description="Insight type (e.g., emerging_opportunity, declining_market, forecast_warning)"
  )
  title: str = Field(..., description="Short title for the insight")
  priority: str = Field(..., description="Priority level: critical, high, moderate, low, monitored")
  description: str = Field(..., description="Detailed description of the insight")
  confidence: Optional[float] = Field(
    None,
    description="Confidence score (0-100)",
    ge=0.0,
    le=100.0
  )
  created_at: str = Field(..., description="ISO 8601 timestamp of creation")
  updated_at: str = Field(..., description="Human-readable timestamp (e.g., '5 minutes ago')")
  style: Optional[InsightStyle] = Field(
    None,
    description="Visual styling configuration for the insight card"
  )
  analysis_basis: Optional[str] = Field(
    None,
    description="Description of the analysis methodology"
  )
  metrics: Optional[dict[str, Any]] = Field(
    None,
    description="Flexible key-value pairs specific to insight type"
  )
  suggested_actions: list[SuggestedAction] = Field(
    default_factory=list,
    description="Higher-level strategic recommendations"
  )
  action_items: list[ActionItem] = Field(
    default_factory=list,
    description="Specific actionable tasks"
  )
  risk_breakdown: Optional[RiskBreakdown] = Field(
    None,
    description="Breakdown of risks by priority level"
  )
  details: Optional[dict[str, Any]] = Field(
    None,
    description="Widget-specific data structure"
  )


class Statistic(BaseModel):
  """A key performance indicator or summary statistic."""
  label: str = Field(..., description="Label for the statistic")
  value: Any = Field(..., description="Value of the statistic (string or number)")
  description: str = Field(..., description="Description of what the statistic represents")
  icon_type: Optional[str] = Field(
    None,
    description="Icon type for visual styling (e.g., refresh, list, plus)"
  )


class RegionGrowth(BaseModel):
  """A region with growth or decline data."""
  name: str = Field(..., description="Name of the region")
  growth: Optional[str] = Field(None, description="Growth percentage (e.g., '+18.7%')")
  decline: Optional[str] = Field(None, description="Decline percentage (e.g., '-8.4%')")


class DiversityPrediction(BaseModel):
  """Diversity shift prediction data."""
  description: str = Field(..., description="Description of the diversity prediction")


class ForecastAction(BaseModel):
  """A suggested action for the forecast."""
  text: str = Field(..., description="Description of the suggested action")
  updated_at: str = Field(..., description="Human-readable timestamp (e.g., '3 hours ago')")


class Forecast(BaseModel):
  """Forecast summary data for the domain."""
  projected_growth: str = Field(..., description="Projected growth percentage (e.g., '+14.2%')")
  top_growth_regions: list[RegionGrowth] = Field(
    default_factory=list,
    description="List of top growth regions"
  )
  declining_regions: list[RegionGrowth] = Field(
    default_factory=list,
    description="List of declining regions"
  )
  diversity_prediction: Optional[DiversityPrediction] = Field(
    None,
    description="Diversity shift prediction"
  )
  suggested_actions: list[ForecastAction] = Field(
    default_factory=list,
    description="List of suggested actions"
  )


class AIInsightResponse(BaseModel):
  """Complete AI Insight response matching the Universal AI Insights API schema.

  This is the root response model that all AI Insight endpoints
  must return. It ensures consistent structure across all domains.
  """
  domain: str = Field(..., description="Domain identifier (energy, education, health)")
  last_updated: str = Field(..., description="ISO 8601 timestamp of last update")
  cache_expires_at: str = Field(..., description="ISO 8601 timestamp when cache expires")
  forecast: Optional[Forecast] = Field(None, description="Forecast summary data")
  metadata: Metadata = Field(..., description="Metadata about the response")
  insights: list[Insight] = Field(default_factory=list, description="List of AI-generated insights")
  statistics: list[Statistic] = Field(default_factory=list, description="Key performance indicators")

  @field_validator('domain')
  @classmethod
  def validate_domain(cls, v: str) -> str:
    """Validate that domain is one of the supported domains."""
    supported = {'energy', 'education', 'health'}
    if v.lower() not in supported:
      raise ValueError(f"Domain must be one of: {supported}")
    return v.lower()

  class Config:
    """Pydantic configuration."""
    json_schema_extra = {
      "example": {
        "domain": "energy",
        "last_updated": "2026-01-29T14:25:00Z",
        "cache_expires_at": "2026-01-29T14:30:00Z",
        "metadata": {
          "total_insights": 1,
          "confidence_average": 94.0,
          "data_sources": [
            {
              "name": "Methane plume data",
              "type": "public",
              "last_updated": "May 2025"
            }
          ]
        },
        "insights": [
          {
            "id": "550e8400-e29b-41d4-a716-446655440010",
            "type": "environmental_risk",
            "title": "Methane Detection Alert",
            "priority": "critical",
            "description": "Detected 94 methane plume-asset intersections in the Permian Basin region.",
            "confidence": 94.0,
            "created_at": "2026-01-29T14:20:00Z",
            "updated_at": "5 minutes ago",
            "analysis_basis": "Based on combined analysis of public and private datasets",
            "metrics": {
              "total_intersections": 94,
              "critical_count": 7,
              "region": "Permian Basin"
            },
            "suggested_actions": [],
            "action_items": [
              {
                "id": "action-energy-001",
                "priority": "critical",
                "description": "Inspect 7 critical assets within 72 hours",
                "deadline": "72 hours",
                "count": 7
              }
            ],
            "risk_breakdown": {
              "critical": 7,
              "high": 23,
              "medium": 15,
              "monitored": 49
            }
          }
        ],
        "statistics": []
      }
    }


# Alias for backwards compatibility
AgentResponse = AIInsightResponse


def validate_insight_response(data: dict) -> AIInsightResponse:
  """Validate a dictionary against the AI Insight schema.

  Args:
      data: Dictionary containing the insight data

  Returns:
      Validated AIInsightResponse instance

  Raises:
      ValidationError: If the data doesn't conform to the schema
  """
  return AIInsightResponse.model_validate(data)
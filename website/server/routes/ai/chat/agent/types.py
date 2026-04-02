from typing import Optional
from pydantic import BaseModel, Field


class WidgetUpdate(BaseModel):
  """Configuration for updating a single widget"""
  variable: str = Field(..., description="Variable DCID to display")
  date: str = Field(default="LATEST", description="Date filter (e.g., '2023', '2024', 'LATEST')")
  place: Optional[str] = Field(default=None, description="Place DCID (e.g., 'geoId/48' for Texas)")
  parentPlace: Optional[str] = Field(default=None, description="Parent place DCID for child place queries")
  childPlaceType: Optional[str] = Field(default=None, description="Type of child places (e.g., 'State', 'County')")
  title: str = Field(..., description="Human-readable title for the widget, include year in format 'Label (year)' if date is specified")


class AgentResponse(BaseModel):
  """Unified response model for AI agent queries"""
  summary: str = Field(..., description="Natural language summary of the answer")
  source: str = Field(..., description="Source of the data")
  widgetIds: list[str] = Field(default_factory=list, description="List of widget IDs to update")
  widgetConfigs: dict[str, WidgetUpdate] = Field(default_factory=dict,
                                                 description="Configuration for each widget keyed by widget ID")

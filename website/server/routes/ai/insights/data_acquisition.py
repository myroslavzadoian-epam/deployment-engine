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
"""Data acquisition layer for AI Insights.

This module handles fetching data from:
- DataCommons MCP (public datasets)
- Private data sources (internal APIs/databases)

Raw data is aggregated and normalized into a common signal structure
before being passed to the Gemini insight agent.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server.services import datacommons as dc

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
  """Get current UTC time with timezone awareness."""
  return datetime.now(timezone.utc)


@dataclass
class DataSourceInfo:
  """Information about a data source."""
  name: str
  type: str  # "public" or "private"
  last_updated: str  # YYYY-MM format


@dataclass
class DomainSignals:
  """Aggregated signals for a domain.

  This is the normalized data structure that gets passed to
  the Gemini insight agent for analysis.
  """
  domain: str
  signals: dict[str, Any] = field(default_factory=dict)
  data_sources: list[DataSourceInfo] = field(default_factory=list)
  fetch_timestamp: datetime = field(default_factory=_utc_now)

  def add_signal(self, key: str, value: Any, source_name: str, source_type: str = "public"):
    """Add a signal to the collection."""
    self.signals[key] = value

    # Track the data source
    source_exists = any(ds.name == source_name for ds in self.data_sources)
    if not source_exists:
      self.data_sources.append(DataSourceInfo(
        name=source_name,
        type=source_type,
        last_updated=_utc_now().strftime("%Y-%m")
      ))

  def to_prompt_format(self) -> str:
    """Convert signals to a format suitable for the Gemini prompt."""
    import json
    return json.dumps(self.signals, indent=2, default=str)


# ==============================================================================
# DataCommons MCP Data Fetching (Public Data)
# ==============================================================================

def _fetch_datacommons_observations(
    variables: list[str],
    place: str = "country/USA",
    child_type: str | None = None
) -> dict[str, Any]:
  """Fetch observations from DataCommons.

  Args:
      variables: list of variable DCIDs to fetch
      place: Place DCID (default: country/USA)
      child_type: If provided, fetch data for child places of this type

  Returns:
      Dictionary of variable -> observation data
  """
  try:
    if child_type:
      # Fetch for child places (e.g., all states)
      result = dc.obs_series_within(place, child_type, variables)
    else:
      # Fetch for a single place
      result = dc.obs_series([place], variables)

    return result.get("byVariable", {})
  except Exception as e:
    logger.error(f"Error fetching DataCommons data: {e}", exc_info=True)
    return {}


def _aggregate_observations(data: dict[str, Any]) -> dict[str, Any]:
  """Aggregate raw observation data into summary statistics.

  Args:
      data: Raw observation data from DataCommons

  Returns:
      Aggregated statistics
  """
  aggregated = {}

  for variable, var_data in data.items():
    by_entity = var_data.get("byEntity", {})

    values = []
    latest_values = []

    for entity_id, entity_data in by_entity.items():
      ordered_facets = entity_data.get("orderedFacets", [])
      for facet in ordered_facets:
        observations = facet.get("observations", [])
        if observations:
          # Get all values
          for obs in observations:
            if "value" in obs:
              values.append(obs["value"])
          # Get latest value
          latest = observations[-1]
          if "value" in latest:
            latest_values.append({
              "entity": entity_id,
              "value": latest["value"],
              "date": latest.get("date", "")
            })

    if values:
      aggregated[variable] = {
        "total": sum(values),
        "count": len(values),
        "average": sum(values) / len(values) if values else 0,
        "min": min(values),
        "max": max(values),
        "latest_by_entity": latest_values[:10]  # Top 10 entities
      }

  return aggregated


# ==============================================================================
# Private Data Fetching
# ==============================================================================

def _fetch_private_data_energy(domain: str) -> dict[str, Any]:
  """Fetch private data for energy domain.

  This is a placeholder that should be replaced with actual
  private data source integration.
  """
  # Example: In production, this would query internal databases
  # For now, return mock data that represents the expected structure
  return {
    "asset_plume_intersections": {
      "total": 94,
      "by_risk_zone": {
        "disadvantaged_communities": 7,
        "near_community_centers": 23,
        "near_schools_hospitals": 15,
        "standard_zones": 49
      }
    },
    "asset_health_scores": {
      "average": 72.5,
      "below_threshold_count": 31,
      "critical_count": 7
    }
  }


def _fetch_private_data_education(domain: str) -> dict[str, Any]:
  """Fetch private data for education domain."""
  return {
    "recruitment_metrics": {
      "total_applicants": 15420,
      "year_over_year_change": -0.03,
      "high_opportunity_regions": 12,
      "declining_interest_regions": 5
    },
    "market_analysis": {
      "top_growth_markets": ["Texas", "Florida", "Arizona"],
      "underperforming_markets": ["Ohio", "Michigan"]
    }
  }


def _fetch_private_data_health(domain: str) -> dict[str, Any]:
  """Fetch private data for health domain."""
  return {
    "coverage_metrics": {
      "uninsured_rate": 0.089,
      "underserved_counties": 234,
      "critical_access_gaps": 18
    },
    "disease_surveillance": {
      "elevated_counties": 45,
      "outbreak_alerts": 2
    }
  }


def _fetch_private_data(domain: str) -> dict[str, Any]:
  """Fetch private data for a domain.

  Routes to the appropriate domain-specific fetcher.
  """
  fetchers = {
    "energy": _fetch_private_data_energy,
    "education": _fetch_private_data_education,
    "health": _fetch_private_data_health,
  }

  fetcher = fetchers.get(domain)
  if fetcher:
    try:
      return fetcher(domain)
    except Exception as e:
      logger.error(f"Error fetching private data for {domain}: {e}")
      return {}

  return {}


# ==============================================================================
# Domain-Specific Signal Fetching
# ==============================================================================

def _fetch_energy_signals() -> DomainSignals:
  """Fetch signals for energy domain."""
  signals = DomainSignals(domain="energy")

  # Fetch public data from DataCommons
  public_vars = [
    "Amount_Emissions_Methane",
    "Amount_Emissions_CarbonDioxide",
    "Count_EnergyFacility",
  ]

  dc_data = _fetch_datacommons_observations(public_vars, child_type="State")
  aggregated = _aggregate_observations(dc_data)

  for var, stats in aggregated.items():
    signals.add_signal(
      f"dc_{var}",
      stats,
      "DataCommons Public Data",
      "public"
    )

  # Fetch private data
  private_data = _fetch_private_data("energy")
  for key, value in private_data.items():
    signals.add_signal(
      key,
      value,
      "Internal Asset Database",
      "private"
    )

  return signals


def _fetch_education_signals() -> DomainSignals:
  """Fetch signals for education domain."""
  signals = DomainSignals(domain="education")

  # Fetch public data from DataCommons
  public_vars = [
    "Median_Income_Household",
    "Count_Person",
    "Count_Person_18To24Years",
  ]

  dc_data = _fetch_datacommons_observations(public_vars, child_type="State")
  aggregated = _aggregate_observations(dc_data)

  for var, stats in aggregated.items():
    signals.add_signal(
      f"dc_{var}",
      stats,
      "DataCommons Demographics",
      "public"
    )

  # Fetch private data
  private_data = _fetch_private_data("education")
  for key, value in private_data.items():
    signals.add_signal(
      key,
      value,
      "Recruitment Dashboard",
      "private"
    )

  return signals


def _fetch_health_signals() -> DomainSignals:
  """Fetch signals for health domain."""
  signals = DomainSignals(domain="health")

  # Fetch public data from DataCommons
  public_vars = [
    "Count_Death",
    "Count_Person_WithHealthInsurance",
    "Percent_Person_WithoutHealthInsurance",
  ]

  dc_data = _fetch_datacommons_observations(public_vars, child_type="State")
  aggregated = _aggregate_observations(dc_data)

  for var, stats in aggregated.items():
    signals.add_signal(
      f"dc_{var}",
      stats,
      "DataCommons Health Data",
      "public"
    )

  # Fetch private data
  private_data = _fetch_private_data("health")
  for key, value in private_data.items():
    signals.add_signal(
      key,
      value,
      "Health Department Records",
      "private"
    )

  return signals


def fetch_domain_signals(domain: str) -> DomainSignals:
  """Fetch all signals for a domain.

  This is the main entry point for data acquisition. It aggregates
  data from DataCommons MCP (public) and private sources into a
  unified signal structure.

  Args:
      domain: Domain identifier (energy, education, health)

  Returns:
      DomainSignals containing all fetched and aggregated data

  Raises:
      ValueError: If domain is not supported
  """
  domain_lower = domain.lower()

  fetchers = {
    "energy": _fetch_energy_signals,
    "education": _fetch_education_signals,
    "health": _fetch_health_signals,
  }

  fetcher = fetchers.get(domain_lower)
  if not fetcher:
    raise ValueError(f"Unsupported domain: {domain}")

  logger.info(f"Fetching signals for domain: {domain}")
  signals = fetcher()
  logger.info(
    f"Fetched {len(signals.signals)} signals from "
    f"{len(signals.data_sources)} data sources for {domain}"
  )

  return signals

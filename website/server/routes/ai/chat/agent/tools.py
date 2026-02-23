"""
Data Commons tools for the chat agent.
These tools serve as a fallback when the MCP server is not available.
Uses the datacommons service library for API calls.
"""

import logging
from typing import Optional

import server.services.datacommons as dc

_logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS = 20
MAX_OBSERVATIONS = 10

DEFAULT_DATE = "LATEST"
DEFAULT_PLACE = "country/USA"


def _parse_observations_from_response(
    data: dict,
    variable: str,
    place: str = DEFAULT_PLACE,
) -> list[dict]:
  """
  Extract observations from Data Commons API response.

  Args:
      data: Raw API response dictionary
      variable: Variable DCID
      place: Place DCID

  Returns:
      List of observation dictionaries with date, value, and facetId
  """
  observations = []
  ordered_facets = (
    data
    .get("byVariable", {})
    .get(variable, {})
    .get("byEntity", {})
    .get(place, {})
    .get("orderedFacets", [])
  )

  for facet in ordered_facets:
    facet_id = facet.get("facetId", "")
    for obs in facet.get("observations", []):
      observations.append({
        "date": obs.get("date", ""),
        "value": obs.get("value"),
        "facetId": facet_id
      })

  return observations


def _filter_and_sort_observations(
    observations: list[dict],
    date: str = DEFAULT_DATE
) -> list[dict]:
  """
  Sort observations by date descending and optionally filter by date.

  Args:
      observations: List of observation dictionaries
      date: Optional date filter (e.g., "2023")

  Returns:
      Filtered and sorted list of observations
  """
  if not observations:
    return observations

  # Sort by date descending
  observations.sort(key=lambda x: x.get("date", ""), reverse=True)

  # Filter by date if specified (and not "LATEST")
  if date and date.upper() != "LATEST":
    filtered = [o for o in observations if o.get("date", "").startswith(date)]
    if filtered:
      return filtered

  return observations


def _build_observations_response(
    observations: list[dict],
    variable: str,
    place: str = DEFAULT_PLACE,
    date: str = DEFAULT_DATE,
    message: Optional[str] = None
) -> dict:
  """
  Build standardized observation response dictionary.

  Args:
      observations: List of observation dictionaries
      variable: Variable DCID
      place: Place DCID
      date: Requested date filter
      message: Optional message for empty results

  Returns:
      Standardized response dictionary
  """
  response = {
    "status": "success",
    "variable": variable,
    "place": place,
    "requestedDate": date,
    "latestObservation": observations[0] if observations else None,
    "allObservations": observations[:MAX_OBSERVATIONS],
    "totalCount": len(observations)
  }

  if message and not observations:
    response["message"] = message

  return response


def search_indicators(
    query: str,
    place: str = DEFAULT_PLACE,
    include_topics: bool = True
) -> dict:
  """
  Search for statistical variable indicators in Data Commons.

  Use this tool FIRST to find variable names/DCIDs for any metric.
  Search by keywords like "applicants", "population", "income", etc.
  Returns variable DCIDs that you need for get_observations.

  Args:
      query: Search query string (e.g., "population", "income", "applicants")
      place: Optional place DCID to filter results (e.g., "geoId/48" for Texas)
      include_topics: Whether to include topic information (default: True, ALWAYS set to true)

  Returns:
      dict: Search results containing matching variables with their DCIDs and descriptions
  """
  _logger.info(f"search_indicators: query='{query}', place='{place}', include_topics={include_topics}")

  try:
    places = [place] if place else []
    data = dc.search_statvar(query, places, sv_only=not include_topics)

    results = [
      {
        "dcid": var.get("dcid", ""),
        "name": var.get("name") or var.get("displayName", ""),
        "description": var.get("description", ""),
        **({"topics": var.get("topics", [])} if include_topics else {})
      }
      for var in data.get("statVars", [])[:MAX_RESULTS]
    ]

    response = {
      "status": "success",
      "query": query,
      "count": len(results),
      "variables": results
    }

    if not results:
      response["message"] = f"No variables found matching '{query}'. Try different search terms."

    return response

  except Exception as e:
    _logger.error(f"Error searching indicators: {e}")
    return {
      "status": "error",
      "query": query,
      "error": str(e),
      "message": "Failed to search indicators in Data Commons"
    }


def get_observations(
    variable: str,
    place: str = DEFAULT_PLACE,
    date: str = DEFAULT_DATE,
) -> dict:
  """
  Fetch statistical observations from Data Commons.

  Use this tool to fetch actual statistical data after finding the variable DCID
  with search_indicators.

  Args:
      variable: Variable DCID (obtained from search_indicators, e.g., "Count_Person")
      place: Place DCID (e.g., "geoId/48" for Texas, "country/USA" for USA)
      date: Optional date filter (e.g., "2023", "2024", "LATEST")

  Returns:
      dict: Observation data containing the statistical value(s)
  """
  _logger.info(f"get_observations: variable='{variable}', place='{place}', date='{date}'")

  try:
    date_param = date if date and date.upper() != "LATEST" else "LATEST"

    # Try point observations first
    data = dc.safe_obs_point([place], [variable], date_param)
    observations = _parse_observations_from_response(data, variable, place)

    # Fallback to time series if no point data
    if not observations:
      try:
        series_data = dc.obs_series([place], [variable])
        observations = _parse_observations_from_response(series_data, variable, place)
      except Exception as e:
        _logger.warning(f"Series fallback failed: {e}")

    observations = _filter_and_sort_observations(observations, date)

    return _build_observations_response(
      observations,
      variable,
      place,
      date,
      message=f"No observations found for variable '{variable}' at place '{place}'"
    )

  except Exception as e:
    _logger.error(f"Error getting observations: {e}")
    return {
      "status": "error",
      "variable": variable,
      "place": place,
      "error": str(e),
      "message": "Failed to fetch observations from Data Commons"
    }


def resolve_place(place_name: str) -> dict:
  """
  Resolve a place name to its DCID.

  Use this tool to convert human-readable place names to Data Commons DCIDs.

  Args:
      place_name: Human-readable place name (e.g., "Texas", "California", "New York City")

  Returns:
      dict: Resolved place information with DCID
  """
  _logger.info(f"resolve_place: place_name='{place_name}'")

  try:
    # Try find_entities API first
    result = dc.find_entities([place_name])
    dcids = result.get(place_name, [])

    if dcids:
      return {
        "status": "success",
        "placeName": place_name,
        "dcid": dcids[0],
        "allDcids": dcids,
        "source": "find_entities"
      }

    # Fallback to recognize_places
    try:
      places = dc.recognize_places(place_name)
      if places and (dcid := places[0].get("dcid")):
        return {
          "status": "success",
          "placeName": place_name,
          "dcid": dcid,
          "source": "recognize_places"
        }
    except Exception as e:
      _logger.warning(f"recognize_places fallback failed: {e}")

    return {
      "status": "not_found",
      "placeName": place_name,
      "message": f"Could not resolve place '{place_name}'. Try using a DCID directly (e.g., 'geoId/48' for Texas)"
    }

  except Exception as e:
    _logger.error(f"Error resolving place: {e}")
    return {
      "status": "error",
      "placeName": place_name,
      "error": str(e)
    }


def get_ranked_places(
    variable: str,
    parent_place: str = DEFAULT_PLACE,
    child_place_type: str = "State",
    date: str = DEFAULT_DATE,
    limit: int = 10,
    ascending: bool = False
) -> dict:
  """
  Get ranked list of places by a statistical variable value.

  Use this tool to answer questions like "Top 10 states by population",
  "Which states have the highest income", "Rank states by opportunity score", etc.
  
  Returns place NAMES (not DCIDs) ranked by the variable value.

  Args:
      variable: Variable DCID (obtained from search_indicators, e.g., "Count_Person")
      parent_place: Parent place DCID containing the child places (default: "country/USA")
      child_place_type: Type of child places to rank (e.g., "State", "County", "City")
      date: Optional date filter (e.g., "2023", "LATEST"). Defaults to latest available.
      limit: Maximum number of results to return (default: 10, max: 100)
      ascending: If True, return lowest values first (default: False for highest first)

  Returns:
      dict: Ranked list of places with their names and values
  """
  _logger.info(f"get_ranked_places: variable='{variable}', parent='{parent_place}', "
               f"child_type='{child_place_type}', date='{date}', limit={limit}, ascending={ascending}")

  try:
    # Cap limit at 100
    limit = min(limit, 100)

    # Get observations for all child places
    date_param = date if date and date.upper() != "LATEST" else "LATEST"
    data = dc.obs_point_within(parent_place, child_place_type, [variable], date_param)

    # Extract observations by place
    place_values = {}
    ordered_facets = (
      data
      .get("byVariable", {})
      .get(variable, {})
      .get("byEntity", {})
    )

    for place_dcid, place_data in ordered_facets.items():
      facets = place_data.get("orderedFacets", [])
      if facets:
        # Get the most recent observation from the first facet
        observations = facets[0].get("observations", [])
        if observations:
          # Sort by date to get the most recent
          observations_sorted = sorted(observations, key=lambda x: x.get("date", ""), reverse=True)
          obs = observations_sorted[0]
          place_values[place_dcid] = {
            "value": obs.get("value"),
            "date": obs.get("date", "")
          }

    if not place_values:
      return {
        "status": "no_data",
        "variable": variable,
        "parentPlace": parent_place,
        "childPlaceType": child_place_type,
        "message": f"No data found for '{variable}' in {child_place_type}s within {parent_place}"
      }

    # Sort by value
    sorted_places = sorted(
      place_values.items(),
      key=lambda x: (x[1]["value"] if x[1]["value"] is not None else float('-inf')),
      reverse=not ascending
    )[:limit]

    # Resolve place DCIDs to names
    place_dcids = [p[0] for p in sorted_places]
    names_data = dc.v2node(place_dcids, "->name")

    place_names = {}
    for dcid, node_data in names_data.get("data", {}).items():
      arcs = node_data.get("arcs", {}).get("name", {}).get("nodes", [])
      if arcs:
        place_names[dcid] = arcs[0].get("value", dcid)
      else:
        place_names[dcid] = dcid

    # Build the ranked list with names
    ranked_list = []
    for rank, (place_dcid, obs_data) in enumerate(sorted_places, 1):
      ranked_list.append({
        "rank": rank,
        "name": place_names.get(place_dcid, place_dcid),
        "dcid": place_dcid,
        "value": obs_data["value"],
        "date": obs_data["date"]
      })

    return {
      "status": "success",
      "variable": variable,
      "parentPlace": parent_place,
      "childPlaceType": child_place_type,
      "totalPlaces": len(place_values),
      "returnedCount": len(ranked_list),
      "order": "ascending" if ascending else "descending",
      "rankedPlaces": ranked_list
    }

  except Exception as e:
    _logger.error(f"Error getting ranked places: {e}")
    return {
      "status": "error",
      "variable": variable,
      "parentPlace": parent_place,
      "childPlaceType": child_place_type,
      "error": str(e),
      "message": "Failed to get ranked places from Data Commons"
    }


def get_dc_tools() -> list:
  """
  Get the list of Data Commons tools for the agent.

  Returns:
      list: List of tool functions
  """
  return [search_indicators, get_observations, resolve_place, get_ranked_places]

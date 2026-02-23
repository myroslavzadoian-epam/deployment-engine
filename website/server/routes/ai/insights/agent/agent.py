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
"""Gemini Insight Agent for AI Insights.

This module contains the Gemini agent that synthesizes domain signals
into structured, actionable insights using Google ADK.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.genai import types

from .types import AIInsightResponse, Metadata, Forecast, RegionGrowth, DiversityPrediction, ForecastAction
from .instructions import AGENT_INSTRUCTIONS
from .tools import get_insights_tools

logger = logging.getLogger(__name__)

# Agent configuration
AGENT_MODEL = os.environ.get("INSIGHT_AGENT_MODEL", "gemini-2.5-flash")
AGENT_NAME = os.environ.get("INSIGHT_AGENT_NAME", "insights_agent")
OUTPUT_KEY = "ai_insights"

# Cache configuration
CACHE_TIMEOUT_MINUTES = 5


def _utc_now() -> datetime:
  """Get current UTC time with timezone awareness."""
  return datetime.now(timezone.utc)


def _format_iso_timestamp(dt: datetime) -> str:
  """Format datetime as ISO 8601 string."""
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_json_from_text(text: str) -> dict | None:
  """Try to extract JSON from text, handling markdown code blocks."""
  if not text:
    return None

  # Clean up response - extract JSON if wrapped in markdown
  cleaned = text.strip()
  if cleaned.startswith("```json"):
    cleaned = cleaned[7:]
  if cleaned.startswith("```"):
    cleaned = cleaned[3:]
  if cleaned.endswith("```"):
    cleaned = cleaned[:-3]
  cleaned = cleaned.strip()

  # Try to find JSON object in the text
  try:
    return json.loads(cleaned)
  except json.JSONDecodeError:
    # Try to find JSON object boundaries
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
      try:
        return json.loads(cleaned[start:end + 1])
      except json.JSONDecodeError:
        pass
  return None


class InsightsAgent:
  """Encapsulates the insights agent logic using Google ADK."""

  def __init__(self, mcp_url: str = None):
    """Initialize the InsightsAgent.

    Args:
        mcp_url: Optional MCP server URL for data access
    """
    self.mcp_url = mcp_url
    self.runner = None

  def _create_runner(self) -> Runner:
    """Creates and configures the ADK Runner."""
    self.runner = Runner(
      app=App(
        name="insights_app",
        root_agent=self.root_agent(),
      ),
      session_service=InMemorySessionService(),
    )
    return self.runner

  def root_agent(self) -> LlmAgent:
    """Create and configure the root LLM agent."""
    return LlmAgent(
      model=AGENT_MODEL,
      name=AGENT_NAME,
      description="Data Commons Insights Agent for domain-specific analysis and recommendations",
      instruction=AGENT_INSTRUCTIONS,
      tools=self.get_tools(),
      output_key=OUTPUT_KEY,
      # Note: output_schema removed to allow flexible JSON output parsing
    )

  def get_tools(self) -> list:
    """Get the list of tools available to the agent."""
    tools = []

    if self.mcp_url:
      tools.append(
        McpToolset(
          connection_params=StreamableHTTPConnectionParams(
            url=self.mcp_url,
            timeout=60,
          )
        )
      )
    else:
      # Use direct insights tools as fallback
      tools.extend(get_insights_tools())

    return tools

  def _get_default_forecast(self, domain: str) -> Forecast | None:
    """Get default forecast data for a domain."""
    if domain == "education":
      return Forecast(
        projected_growth="+14.2%",
        top_growth_regions=[
          RegionGrowth(name="Austin Metro", growth="+18.7%"),
          RegionGrowth(name="San Antonio", growth="+16.3%"),
          RegionGrowth(name="Dallas-Fort Worth", growth="+15.1%"),
        ],
        declining_regions=[
          RegionGrowth(name="Rural West Texas", decline="-8.4%"),
          RegionGrowth(name="Amarillo Metro", decline="-5.2%"),
          RegionGrowth(name="Wichita Falls", decline="-3.7%"),
        ],
        diversity_prediction=DiversityPrediction(
          description="Hispanic student population projected +22% in Houston, Corpus Christi, and El Paso metro areas by 2027"
        ),
        suggested_actions=[
          ForecastAction(
            text="Increase travel or virtual outreach in Texas and Ohio - high potential + low applicants.",
            updated_at="3 hours ago"
          ),
          ForecastAction(
            text="Reallocate 12% of digital campaign budget to rising Florida ZIP codes.",
            updated_at="2 hours ago"
          ),
        ]
      )
    return None

  def _create_empty_response(self, domain: str) -> AIInsightResponse:
    """Create an empty response with proper structure."""
    now = _utc_now()
    cache_expires = now + timedelta(minutes=CACHE_TIMEOUT_MINUTES)

    return AIInsightResponse(
      domain=domain,
      last_updated=_format_iso_timestamp(now),
      cache_expires_at=_format_iso_timestamp(cache_expires),
      forecast=self._get_default_forecast(domain),
      metadata=Metadata(
        total_insights=0,
        confidence_average=0.0,
        data_sources=[]
      ),
      insights=[],
      statistics=[]
    )

  def _parse_response(self, chat_state: dict | str | None, domain: str) -> AIInsightResponse:
    """Parse the agent's response into AIInsightResponse.

    The chat_state can be:
    - A dict (already parsed)
    - A JSON string
    - A JSON string wrapped in markdown code blocks
    """
    now = _utc_now()
    cache_expires = now + timedelta(minutes=CACHE_TIMEOUT_MINUTES)

    if chat_state is None:
      logger.warning("Agent did not produce a response (chat_state is None)")
      return self._create_empty_response(domain)

    # If already a dict, use it directly
    if isinstance(chat_state, dict):
      # Ensure required fields are present
      chat_state.setdefault("domain", domain)
      chat_state.setdefault("last_updated", _format_iso_timestamp(now))
      chat_state.setdefault("cache_expires_at", _format_iso_timestamp(cache_expires))
      chat_state.setdefault("metadata", {
        "total_insights": len(chat_state.get("insights", [])),
        "confidence_average": 0.0,
        "data_sources": []
      })
      chat_state.setdefault("insights", [])
      chat_state.setdefault("statistics", [])
      
      # Add default forecast if not present
      if "forecast" not in chat_state or chat_state["forecast"] is None:
        default_forecast = self._get_default_forecast(domain)
        if default_forecast:
          chat_state["forecast"] = default_forecast.model_dump()

      # Calculate confidence average if insights exist
      insights = chat_state.get("insights", [])
      if insights:
        confidences = [i.get("confidence", 0) for i in insights if i.get("confidence") is not None]
        if confidences:
          chat_state["metadata"]["confidence_average"] = sum(confidences) / len(confidences)
        chat_state["metadata"]["total_insights"] = len(insights)

      return AIInsightResponse(**chat_state)

    # It's a string - need to parse it
    if not isinstance(chat_state, str):
      logger.warning(f"Unexpected chat_state type: {type(chat_state)}")
      return self._create_empty_response(domain)

    # Try to extract JSON from the string
    parsed = _extract_json_from_text(chat_state)
    if parsed and isinstance(parsed, dict):
      return self._parse_response(parsed, domain)

    logger.warning(f"Failed to parse response as JSON: {chat_state[:200]}...")
    return self._create_empty_response(domain)

  def _extract_response_from_events(self, events: list) -> dict | str | None:
    """Extract the model response from a list of events."""
    last_text_response = None
    last_json_response = None

    for event in events:
      event_type = type(event).__name__

      # Try multiple ways to extract content from events
      text_content = None

      # Method 1: event.content.parts[].text
      if hasattr(event, 'content') and event.content:
        content_obj = event.content
        if hasattr(content_obj, 'parts') and content_obj.parts:
          for part in content_obj.parts:
            if hasattr(part, 'text') and part.text:
              text_content = part.text

      # Method 2: event.text
      if not text_content and hasattr(event, 'text') and event.text:
        text_content = event.text

      # Method 3: event.response.text
      if not text_content and hasattr(event, 'response') and event.response:
        resp = event.response
        if hasattr(resp, 'text') and resp.text:
          text_content = resp.text

      # Method 4: event.model_response (for some ADK versions)
      if not text_content and hasattr(event, 'model_response') and event.model_response:
        model_resp = event.model_response
        if hasattr(model_resp, 'text') and model_resp.text:
          text_content = model_resp.text
        elif hasattr(model_resp, 'content') and model_resp.content:
          if hasattr(model_resp.content, 'parts'):
            for part in model_resp.content.parts:
              if hasattr(part, 'text') and part.text:
                text_content = part.text

      # Method 5: Direct dict in event.data or event.result
      if hasattr(event, 'data') and isinstance(event.data, dict):
        if 'insights' in event.data or 'domain' in event.data:
          last_json_response = event.data

      if hasattr(event, 'result') and isinstance(event.result, dict):
        if 'insights' in event.result or 'domain' in event.result:
          last_json_response = event.result

      if text_content:
        last_text_response = text_content
        # Try to parse as JSON immediately
        parsed = _extract_json_from_text(text_content)
        if parsed and isinstance(parsed, dict):
          if 'insights' in parsed or 'domain' in parsed:
            last_json_response = parsed

      logger.debug(f"Event {event_type}: text={bool(text_content)}, json={bool(last_json_response)}")

    # Prefer JSON response over text
    if last_json_response:
      return last_json_response
    return last_text_response

  async def run(self, domain: str, query: str = None) -> AIInsightResponse:
    """Executes the insights agent for a given domain.

    Args:
        domain: Domain identifier (energy, education, health)
        query: Optional additional query to refine insights

    Returns:
        AIInsightResponse with domain insights
    """
    if not self.runner:
      self._create_runner()

    max_retries = 3
    for attempt in range(max_retries):
      ephemeral_session_id = str(uuid.uuid4())
      generic_user = "stateless-web-user"

      try:
        session = await self.runner.session_service.create_session(
          app_name=self.runner.app_name,
          session_id=ephemeral_session_id,
          user_id=generic_user,
        )

        # Build the user message with explicit JSON output instruction
        if query:
          user_message = f"Analyze the {domain} domain and respond to: {query}"
        else:
          user_message = (
            f"Generate comprehensive insights for the {domain} domain. "
            f"Use the get_domain_signals and get_domain_context tools to fetch data, "
            f"then analyze the patterns and generate insights. "
            f"Your final response MUST be a valid JSON object with this structure: "
            f'{{"domain": "{domain}", "insights": [...], "statistics": [...], "metadata": {{...}}}}'
          )

        content = types.Content(role="user", parts=[types.Part(text=user_message)])

        # Run the agent and capture all events
        all_events = []

        async for event in self.runner.run_async(
            new_message=content,
            user_id=session.user_id,
            session_id=session.id
        ):
          all_events.append(event)
          event_type = type(event).__name__
          logger.debug(f"Event [{len(all_events)}]: type={event_type}, attrs={dir(event)[:5]}...")

        logger.info(f"Processed {len(all_events)} events from runner")

        # Get updated session state
        updated_session = await self.runner.session_service.get_session(
          app_name=self.runner.app_name,
          user_id=session.user_id,
          session_id=session.id
        )

        # Try to get response from session state first
        chat_state = updated_session.state.get(OUTPUT_KEY)
        logger.debug(f"Session state keys: {list(updated_session.state.keys())}")

        # If not in session state, extract from events
        if chat_state is None:
          logger.info("OUTPUT_KEY not in session state, extracting from events...")
          chat_state = self._extract_response_from_events(all_events)

        # If still no response, check all session state keys for potential response
        if chat_state is None:
          for key, value in updated_session.state.items():
            if isinstance(value, dict) and ('insights' in value or 'domain' in value):
              logger.info(f"Found response in session state key: {key}")
              chat_state = value
              break
            elif isinstance(value, str):
              parsed = _extract_json_from_text(value)
              if parsed and isinstance(parsed, dict) and ('insights' in parsed or 'domain' in parsed):
                logger.info(f"Found JSON response in session state key: {key}")
                chat_state = parsed
                break

        if chat_state:
          logger.info(f"Successfully extracted response: type={type(chat_state).__name__}")
        else:
          logger.warning("No response found in session state or events")

        response = self._parse_response(chat_state, domain)

        # Ensure domain is set correctly
        if response.domain == "unknown" or not response.domain:
          response = response.model_copy(update={"domain": domain})

        return response

      except Exception as e:
        logger.warning(f"Attempt {attempt + 1} failed: {e}")
        if attempt == max_retries - 1:
          raise
      finally:
        if self.runner:
          await self.runner.session_service.delete_session(
            app_name=self.runner.app_name,
            user_id=generic_user,
            session_id=ephemeral_session_id
          )
          # Close MCP toolset connections
          for toolset in self.runner.agent.tools:
            if hasattr(toolset, 'close') and callable(toolset.close):
              try:
                await toolset.close()
              except Exception:
                pass


def create_insights_agent(mcp_url: str = None) -> InsightsAgent:
  """Create and return an InsightsAgent instance.

  Args:
      mcp_url: Optional MCP server URL for data access

  Returns:
      Configured InsightsAgent instance
  """
  return InsightsAgent(mcp_url=mcp_url)
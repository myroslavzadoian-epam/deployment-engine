import asyncio
import json
import os
import logging
import uuid

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.genai import types

from pydantic import BaseModel, Field

from .instructions import AGENT_INSTRUCTIONS, get_agent_instructions
from .types import AgentResponse
from .tools import get_dc_tools

_logger = logging.getLogger(__name__)

AGENT_MODEL = os.environ.get("AGENT_MODEL", "gemini-2.5-flash")
AGENT_NAME = os.environ.get("AGENT_NAME", "datacommons_agent")
OUTPUT_KEY = "ai_chat"


class Context(BaseModel):
  """Configuration for a single widget"""
  parent_place: str = Field(default='country/USA')
  child_place_type: str = Field(default='State')


class ChatAgent:
  """Encapsulates the chat agent logic."""

  def __init__(self, mcp_url: str = None, domain: str = None):
    """Initialize the ChatAgent.

    Args:
        mcp_url: Optional MCP server URL for data access
        domain: Domain identifier (education, energy, health, etc.)
    """
    self.mcp_url = mcp_url
    self.domain = domain
    self.runner = None
    self._instructions = None

  def _get_instructions(self) -> str:
    """Get the instructions for the agent."""
    if self._instructions is None:
      try:
        self._instructions = get_agent_instructions(self.domain)
        _logger.info("Loaded agent instructions from config")
      except Exception as e:
        _logger.warning(f"Failed to load config: {e}. Using default instructions.")
        self._instructions = AGENT_INSTRUCTIONS
    return self._instructions

  def _create_runner(self) -> Runner:
    """Creates and configures the ADK Runner."""
    self.runner = Runner(
      app=App(
        name="agents",
        root_agent=self.root_agent(),
      ),
      session_service=InMemorySessionService(),
    )
    return self.runner

  def root_agent(self) -> LlmAgent:
    return LlmAgent(
      model=AGENT_MODEL,
      name=AGENT_NAME,
      description="Talk to Your Datacommons Data",
      instruction=self._get_instructions(),
      tools=self.get_tools(),
      output_key=OUTPUT_KEY,
      #output_schema=AgentResponse, # is not stable with tools, so parsing on our side
    )

  def get_tools(self) -> list:
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
      tools.extend(get_dc_tools())
    return tools

  def _parse_response(self, chat_state) -> AgentResponse:
    """Parse the agent's response into AgentResponse."""
    if chat_state is None:
      _logger.warning("Agent did not produce a response")
      return AgentResponse(
        summary="I was unable to complete the request. Please try again.",
        source="Error"
      )

    # Already a dict - use directly
    if isinstance(chat_state, dict):
      return AgentResponse(**chat_state)

    # Handle string responses
    if not isinstance(chat_state, str):
      return AgentResponse(summary=str(chat_state), source="Agent response")

    # Extract JSON from markdown code blocks if present
    response_text = chat_state.strip()
    if response_text.startswith("```"):
      lines = response_text.split("\n")
      # Remove first line (```json or ```)
      lines = lines[1:]
      # Remove last line if it's the closing ```
      if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
      response_text = "\n".join(lines).strip()

    try:
      parsed = json.loads(response_text) if response_text.startswith("{") else response_text
      if isinstance(parsed, dict):
        return AgentResponse(**parsed)
      return AgentResponse(summary=str(parsed), source="Agent response")
    except json.JSONDecodeError as e:
      _logger.warning(f"Failed to parse response as JSON: {e}")
      raise ValueError("Agent response is not valid JSON")

  async def run(self, query: str) -> AgentResponse:
    """Executes the agent for a given query."""
    if not self.runner:
      self._create_runner()

    session_id = str(uuid.uuid4())
    user_id = "stateless-web-user"

    try:
      session = await self.runner.session_service.create_session(
        app_name=self.runner.app_name,
        session_id=session_id,
        user_id=user_id,
      )

      content = types.Content(role="user", parts=[types.Part(text=query)])

      # Collect responses from the agent
      last_response = None
      async for event in self.runner.run_async(
        new_message=content,
        user_id=session.user_id,
        session_id=session.id
      ):
        # Capture text responses from events
        if hasattr(event, 'content') and event.content:
          if hasattr(event.content, 'parts') and event.content.parts:
            for part in event.content.parts:
              if hasattr(part, 'text') and part.text:
                last_response = part.text
                _logger.info("AI EVENT: %s", last_response)

      # Get final state from session
      updated_session = await self.runner.session_service.get_session(
        app_name=self.runner.app_name,
        user_id=session.user_id,
        session_id=session.id
      )

      chat_state = updated_session.state.get(OUTPUT_KEY) or last_response
      _logger.info("AI FINAL: %s", chat_state)

      return self._parse_response(chat_state)

    except Exception as e:
      _logger.exception("Agent execution failed: %s", str(e))
      return AgentResponse(
        summary="I was unable to complete the request. Please try again.",
        source="Error"
      )
    finally:
      await self._cleanup_session(user_id, session_id)

  async def _cleanup_session(self, user_id: str, session_id: str):
    """Clean up session and close tool connections."""
    if not self.runner:
      return

    try:
      await self.runner.session_service.delete_session(
        app_name=self.runner.app_name,
        user_id=user_id,
        session_id=session_id
      )
    except Exception as e:
      _logger.warning(f"Failed to delete session: {e}")

    # Close MCP toolset connections
    for toolset in self.runner.agent.tools:
      if hasattr(toolset, 'close') and callable(toolset.close):
        try:
          result = toolset.close()
          if asyncio.iscoroutine(result):
            await result
        except Exception as e:
          _logger.warning(f"Failed to close toolset: {e}")


def create_chat_agent(mcp_url: str = None, domain: str = None) -> ChatAgent:
  """Creates a ChatAgent instance.

  Args:
      mcp_url: Optional MCP server URL for data access
      domain: Domain identifier (education, energy, health, etc.)

  Returns:
      ChatAgent configured for the specified domain
  """
  return ChatAgent(mcp_url, domain=domain)
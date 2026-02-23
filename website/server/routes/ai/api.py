import logging
import os

from flask import Blueprint, request, jsonify

from .chat.agent.types import AgentResponse as ChatAgentResponse
from .chat.agent.agent import create_chat_agent

logger = logging.getLogger(__name__)

bp = Blueprint('ai_api', __name__, url_prefix='/api/ai')

# Supported domains for insights and chat
SUPPORTED_DOMAINS = frozenset({"energy", "education", "health"})

# Agent instances (lazily initialized, keyed by domain)
_chat_agents: dict = {}


def _get_chat_agent(domain: str = None):
  """Get or create a chat agent for the specified domain."""
  global _chat_agents
  cache_key = domain or "__default__"

  if cache_key not in _chat_agents:
    _chat_agents[cache_key] = create_chat_agent(
      mcp_url=os.environ.get("MCP_URL"),
      domain=domain
    )
  return _chat_agents[cache_key]


@bp.route('/chat', methods=['POST'])
async def chat():
  """
  Agent-based endpoint that handles both configurational and analytical queries.
  Uses Google ADK with DataCommons MCP tools.

  Request Body:
      query: The user's question (required)
      domain: Domain context (optional) - one of 'energy', 'education', 'health'
  """
  query = request.json.get("query")
  if not query:
    return jsonify({"error": "Query not provided"}), 400

  domain = request.json.get("domain")
  if domain and domain.lower() not in SUPPORTED_DOMAINS:
    return jsonify({
      "error": "Unsupported domain",
      "message": f"Domain '{domain}' is not supported. Supported domains: {', '.join(sorted(SUPPORTED_DOMAINS))}",
      "supported_domains": list(sorted(SUPPORTED_DOMAINS))
    }), 400

  try:
    agent = _get_chat_agent(domain.lower() if domain else None)

    result: ChatAgentResponse = await agent.run(query)
    return result.model_dump_json()

  except Exception as e:
    logger.exception("Failed to process AI agent query: %s", e)
    return jsonify({"error": f"Failed to process AI agent query: {e}"}), 500


@bp.route('/chat/<domain>', methods=['POST'])
async def chat_with_domain(domain: str):
  """
  Domain-specific chat endpoint.
  Uses domain-specific instructions for the chat agent.

  Path Parameters:
      domain: One of 'energy', 'education', 'health'

  Request Body:
      query: The user's question (required)
  """
  # Validate domain
  domain_lower = domain.lower()
  if domain_lower not in SUPPORTED_DOMAINS:
    return jsonify({
      "error": "Unsupported domain",
      "message": f"Domain '{domain}' is not supported. Supported domains: {', '.join(sorted(SUPPORTED_DOMAINS))}",
      "supported_domains": list(sorted(SUPPORTED_DOMAINS))
    }), 400

  query = request.json.get("query")
  if not query:
    return jsonify({"error": "Query not provided"}), 400

  try:
    agent = _get_chat_agent(domain_lower)

    result: ChatAgentResponse = await agent.run(query)
    return result.model_dump_json()

  except Exception as e:
    logger.exception("Failed to process AI agent query for domain %s: %s", domain, e)
    return jsonify({"error": f"Failed to process AI agent query: {e}"}), 500

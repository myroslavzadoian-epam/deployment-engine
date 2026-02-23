import logging
import os
import time

from flask import Blueprint, request, jsonify

from .chat.agent.types import AgentResponse as ChatAgentResponse
from .chat.agent.agent import create_chat_agent
from .insights.agent.types import AIInsightResponse
from .insights.agent.agent import create_insights_agent
import server.lib.cache as lib_cache

logger = logging.getLogger(__name__)

bp = Blueprint('ai_api', __name__, url_prefix='/api/ai')

# Supported domains for insights and chat
SUPPORTED_DOMAINS = frozenset({"energy", "education", "health"})

# Agent instances (lazily initialized, keyed by domain)
_chat_agents: dict = {}
_insights_agent = None

# Cache key prefix for insights
INSIGHTS_CACHE_PREFIX = "ai_insights_"
# Cache timeout: 1 hour (3600 seconds)
INSIGHTS_CACHE_TIMEOUT = 3600


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


@bp.route("/insights/<domain>")
async def get_insights(domain: str):
  """Generate AI insights for a specific domain.

  GET /api/ai/insights/<domain>

  Path Parameters:
      domain: One of 'energy', 'education', 'health'

  Query Parameters:
      query: Optional additional query to refine insights

  Returns:
      JSON response conforming to the canonical AI Insight schema

  Errors:
      400: Unsupported domain
      500: Internal error during insight generation
  """
  # Validate domain
  domain_lower = domain.lower()
  if domain_lower not in SUPPORTED_DOMAINS:
    logger.warning(f"Unsupported domain requested: {domain}")
    return jsonify({
      "error": "Unsupported domain",
      "message": f"Domain '{domain}' is not supported. Supported domains: {', '.join(sorted(SUPPORTED_DOMAINS))}",
      "supported_domains": list(sorted(SUPPORTED_DOMAINS))
    }), 400

  # Optional query parameter for refined insights
  query = request.args.get('query')

  # Build cache key
  cache_key = f"{INSIGHTS_CACHE_PREFIX}{domain_lower}_{query or 'default'}"
  
  # Check cache (using Flask's model_cache which persists to filesystem/redis)
  cached_response = lib_cache.model_cache.get(cache_key)
  logger.info(f"[PID={os.getpid()}] Cache check: key={cache_key}, hit={cached_response is not None}")
  if cached_response is not None:
    logger.info(f"[PID={os.getpid()}] Cache hit for insights {cache_key}")
    return cached_response, 200, {'Content-Type': 'application/json'}

  start_time = time.time()

  try:
    global _insights_agent
    if _insights_agent is None:
      _insights_agent = create_insights_agent(mcp_url=os.environ.get("MCP_URL"))

    result: AIInsightResponse = await _insights_agent.run(domain_lower, query)

    # Update cache
    json_response = result.model_dump_json()
    lib_cache.model_cache.set(cache_key, json_response, timeout=INSIGHTS_CACHE_TIMEOUT)
    logger.info(f"[PID={os.getpid()}] Cache store: key={cache_key}")

    elapsed = time.time() - start_time
    logger.info(f"Generated insight for {domain_lower} in {elapsed:.2f}s")

    return json_response, 200, {'Content-Type': 'application/json'}

  except Exception as e:
    logger.exception("Failed to generate insights for domain %s: %s", domain, e)
    return jsonify({
      "error": "Internal server error",
      "message": f"Failed to generate AI insights: {e}"
    }), 500


@bp.route("/insights/<domain>/refresh")
async def insights_domain_refresh(domain: str):
  """Force refresh of AI insights for a domain.

  POST /api/ai/insights/<domain>/refresh

  This endpoint forces a fresh generation of insights.

  Path Parameters:
      domain: One of 'energy', 'education', 'health'

  Returns:
      JSON response with the refreshed insight
  """
  # Validate domain
  domain_lower = domain.lower()
  if domain_lower not in SUPPORTED_DOMAINS:
    return jsonify({
      "error": "Unsupported domain",
      "message": f"Domain '{domain}' is not supported."
    }), 400

  # Invalidate cache for this domain
  # Note: FileSystemCache doesn't support pattern deletion, so we delete the known key
  query = request.args.get('query')
  cache_key = f"{INSIGHTS_CACHE_PREFIX}{domain_lower}_{query or 'default'}"
  lib_cache.model_cache.delete(cache_key)
  logger.info(f"[PID={os.getpid()}] Cache invalidated: key={cache_key}")

  # Delegate to main endpoint
  return await get_insights(domain_lower)

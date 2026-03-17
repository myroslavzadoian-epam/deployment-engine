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
"""Domain context configuration for AI Insights.

Each domain defines:
- Relevant metrics and variables
- Risk classification criteria
- Action templates and time horizons
- Regulatory context
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from google.cloud import storage
from shared.lib.gcs import is_gcs_path, get_path_parts

logger = logging.getLogger(__name__)

# Supported domains
SUPPORTED_DOMAINS = frozenset({"energy", "education", "health"})

INPUT_DIR = os.getenv('INPUT_DIR', '')
AI_INSIGHTS_CONFIG_PATH = 'input_data/ai_insights.json'


def _load_config_from_storage() -> dict | None:
  """Load ai_chat.json from GCS or local filesystem."""
  if not INPUT_DIR:
    logger.warning("INPUT_DIR not set")
    return None

  if is_gcs_path(INPUT_DIR):
    client = storage.Client()
    bucket_name, _ = get_path_parts(INPUT_DIR)
    bucket = client.bucket(bucket_name)
    blob = bucket.get_blob(AI_INSIGHTS_CONFIG_PATH)

    if not blob:
      logger.warning(f"Config not found in GCS: {AI_INSIGHTS_CONFIG_PATH}")
      return None

    return json.loads(blob.download_as_bytes())
  else:
    local_base_folder = INPUT_DIR.rsplit('/', 1)[0]
    filepath = os.path.join(local_base_folder, AI_INSIGHTS_CONFIG_PATH)

    if not os.path.exists(filepath):
      logger.warning(f"Config not found locally: {filepath}")
      return None

    with open(filepath) as f:
      return json.load(f)


@dataclass
class RiskCriteria:
  """Risk classification criteria for a domain."""
  critical: str
  high: str
  medium: str
  monitored: str


@dataclass
class MetricDefinition:
  """Definition of a metric used in the domain."""
  name: str
  dcid: str
  description: str
  unit: str | None = None
  is_private: bool = False


@dataclass
class ActionTemplate:
  """Template for a suggested action."""
  action_id: str
  label_template: str
  priority: str
  time_horizon: str


@dataclass
class DomainContext:
  """Complete context for a domain used in AI Insight generation.

  This context is injected into the Gemini prompt to provide
  domain-specific knowledge for risk analysis and recommendations.
  """
  domain: str
  display_name: str
  description: str
  risk_criteria: RiskCriteria
  regulatory_context: str
  time_horizon: str
  metrics: list[MetricDefinition] = field(default_factory=list)
  action_templates: list[ActionTemplate] = field(default_factory=list)

  def to_prompt_context(self) -> str:
    """Convert domain context to a string for Gemini prompt injection."""
    return f"""
DOMAIN: {self.display_name}
{self.description}

RISK CLASSIFICATION CRITERIA:
- Critical: {self.risk_criteria.critical}
- High: {self.risk_criteria.high}
- Medium: {self.risk_criteria.medium}
- Monitored: {self.risk_criteria.monitored}

REGULATORY CONTEXT: {self.regulatory_context}

TIME HORIZON: {self.time_horizon}

AVAILABLE METRICS:
{self._format_metrics()}

ACTION TEMPLATES:
{self._format_actions()}
"""

  def _format_metrics(self) -> str:
    """Format metrics for prompt."""
    if not self.metrics:
      return "No specific metrics defined."

    lines = []
    for m in self.metrics:
      source = "(private)" if m.is_private else "(public)"
      unit = f" [{m.unit}]" if m.unit else ""
      lines.append(f"- {m.name} ({m.dcid}){unit} {source}: {m.description}")
    return "\n".join(lines)

  def _format_actions(self) -> str:
    """Format action templates for prompt."""
    if not self.action_templates:
      return "No specific action templates defined."

    lines = []
    for a in self.action_templates:
      lines.append(f"- [{a.priority.upper()}] {a.label_template} (within {a.time_horizon})")
    return "\n".join(lines)


# Cache for loaded domain contexts
_domain_context_cache: dict[str, DomainContext] = {}


def _load_domain_context_from_json(domain: str) -> DomainContext:
  """Load domain context from a JSON configuration file.

  Args:
      domain: Domain identifier

  Returns:
      DomainContext loaded from the JSON file

  Raises:
      ValueError: If the JSON file doesn't exist or is invalid
  """

  config_data = _load_config_from_storage()

  # Parse the configuration
  risk_criteria = RiskCriteria(**config_data.get("risk_criteria", {}))

  metrics = [
    MetricDefinition(**m)
    for m in config_data.get("metrics", [])
  ]

  action_templates = [
    ActionTemplate(**a)
    for a in config_data.get("action_templates", [])
  ]

  return DomainContext(
    domain=domain,
    display_name=config_data.get("display_name", domain.title()),
    description=config_data.get("description", ""),
    risk_criteria=risk_criteria,
    regulatory_context=config_data.get("regulatory_context", ""),
    time_horizon=config_data.get("time_horizon", ""),
    metrics=metrics,
    action_templates=action_templates,
  )


def get_domain_context(domain: str) -> DomainContext:
  """Get the domain context for a specific domain.

  Loads the context from server/config/custom_dc/<domain>/ai_insights.json.
  Results are cached for performance.

  Args:
      domain: Domain identifier (energy, education, health)

  Returns:
      DomainContext for the specified domain

  Raises:
      ValueError: If domain is not supported or configuration is invalid
  """
  domain_lower = domain.lower()
  if domain_lower not in SUPPORTED_DOMAINS:
    raise ValueError(
      f"Unsupported domain: {domain}. "
      f"Supported domains: {', '.join(sorted(SUPPORTED_DOMAINS))}"
    )

  # Check cache first
  if domain_lower in _domain_context_cache:
    return _domain_context_cache[domain_lower]

  # Load from JSON file
  context = _load_domain_context_from_json(domain_lower)
  _domain_context_cache[domain_lower] = context
  return context

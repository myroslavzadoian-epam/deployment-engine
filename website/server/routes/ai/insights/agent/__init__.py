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
"""Agent module for AI Insights.

This module provides the InsightsAgent class and related tools for
generating domain-specific AI insights using the Google ADK framework.
"""

from .agent import (
    InsightsAgent,
    create_insights_agent,
    AGENT_MODEL,
    AGENT_NAME,
    OUTPUT_KEY,
)

from .types import (
    AIInsightResponse,
    AgentResponse,
    Insight,
    SuggestedAction,
    ActionItem,
    RiskBreakdown,
    DataSource,
    Metadata,
    Statistic,
    Priority,
    DataSourceType,
    validate_insight_response,
)

from .instructions import (
    AGENT_INSTRUCTIONS,
)

from .tools import (
    get_insights_tools,
    get_domain_signals,
    get_domain_context,
    analyze_risk_patterns,
    generate_insight_template,
)

__all__ = [
    # Agent class and factory
    "InsightsAgent",
    "create_insights_agent",
    # Types
    "AIInsightResponse",
    "AgentResponse",
    "Insight",
    "SuggestedAction",
    "ActionItem",
    "RiskBreakdown",
    "DataSource",
    "Metadata",
    "Statistic",
    "Priority",
    "DataSourceType",
    "validate_insight_response",
    # Tools
    "get_insights_tools",
    "get_domain_signals",
    "get_domain_context",
    "analyze_risk_patterns",
    "generate_insight_template",
    # Constants
    "AGENT_MODEL",
    "AGENT_NAME",
    "OUTPUT_KEY",
    "AGENT_INSTRUCTIONS",
]
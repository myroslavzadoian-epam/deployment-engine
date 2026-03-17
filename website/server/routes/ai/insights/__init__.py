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
"""AI Insights module for domain-specific intelligence.

Provides the Universal AI Insights API with support for education,
energy, and health domains.
"""

from .agent.types import (
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
from .domain_context import (
  DomainContext,
  get_domain_context,
  SUPPORTED_DOMAINS,
)

__all__ = [
  # Schema
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
  # Domain Context
  "DomainContext",
  "get_domain_context",
  "SUPPORTED_DOMAINS",
]

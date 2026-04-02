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
"""Domain context configuration for AI Chat Agent."""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from google.cloud import storage
from shared.lib.gcs import is_gcs_path, get_path_parts

logger = logging.getLogger(__name__)

INPUT_DIR = os.getenv('INPUT_DIR', '')
AI_CHAT_CONFIG_PATH = 'ai_chat.json'


def _load_config_from_storage() -> dict | None:
    """Load ai_chat.json from GCS or local filesystem."""
    if not INPUT_DIR:
        logger.warning("INPUT_DIR not set")
        return None

    if is_gcs_path(INPUT_DIR):
        client = storage.Client()
        bucket_name, blob_name = get_path_parts(INPUT_DIR)
        bucket = client.bucket(bucket_name)
        
        ai_chat_blob_path = f'{blob_name}/{AI_CHAT_CONFIG_PATH}'
        blob = bucket.get_blob(ai_chat_blob_path)

        if not blob:
            logger.warning(f"Config not found in GCS: {ai_chat_blob_path}")
            return None

        return json.loads(blob.download_as_bytes())
    else:
        filepath = os.path.join(INPUT_DIR, AI_CHAT_CONFIG_PATH)

        if not os.path.exists(filepath):
            logger.warning(f"Config not found locally: {filepath}")
            return None

        with open(filepath) as f:
            return json.load(f)


@dataclass
class WidgetDefinition:
    """Definition of a widget used in the domain."""
    id: str
    description: str
    default_variable: str | None = None
    supports: list[str] = field(default_factory=list)


@dataclass
class PlaceExample:
    """Example place mapping."""
    name: str
    dcid: str


@dataclass
class QueryExample:
    """Example query with steps."""
    question: str
    steps: list[str]


@dataclass
class ResponseExample:
    """Example response format."""
    type: str
    example: dict[str, Any]


@dataclass
class ChatDomainContext:
    """Complete context for a domain used in AI Chat agent."""
    domain: str
    display_name: str
    description: str
    assistant_role: str
    search_keywords: list[str] = field(default_factory=list)
    place_examples: list[PlaceExample] = field(default_factory=list)
    widgets: list[WidgetDefinition] = field(default_factory=list)
    widget_selection_rules: list[str] = field(default_factory=list)
    example_queries: list[QueryExample] = field(default_factory=list)
    response_examples: list[ResponseExample] = field(default_factory=list)

    def get_widgets_text(self) -> str:
        """Format widgets for prompt."""
        if not self.widgets:
            return "No widgets defined."

        lines = []
        for w in self.widgets:
            supports = ", ".join(w.supports) if w.supports else "none"
            lines.append(f"- **{w.id}**: {w.description} (supports: {supports})")
        return "\n".join(lines)

    def get_widget_selection_rules_text(self) -> str:
        """Format widget selection rules for prompt."""
        if not self.widget_selection_rules:
            return ""
        
        lines = ["## Widget Selection Guide"]
        for rule in self.widget_selection_rules:
            lines.append(f"- {rule}")
        return "\n".join(lines)

    def get_place_dcids_text(self) -> str:
        """Format place examples for prompt."""
        lines = []
        for p in self.place_examples:
            lines.append(f"- {p.name} = {p.dcid}")
        if not lines:
            lines.append("- USA = country/USA")
        return "\n".join(lines)

    def get_search_keywords_text(self) -> str:
        """Format search keywords for prompt."""
        if not self.search_keywords:
            return "domain-specific terms"
        return ", ".join(f'"{kw}"' for kw in self.search_keywords)

    def get_example_queries_text(self) -> str:
        """Format example queries for prompt."""
        if not self.example_queries:
            return ""

        sections = []
        for ex in self.example_queries:
            steps = "\n".join(f"   {i}. {step}" for i, step in enumerate(ex.steps, 1))
            sections.append(f"**Q:** {ex.question}\n{steps}")
        return "\n\n".join(sections)

    def get_response_examples_text(self) -> str:
        """Format response examples for prompt."""
        if not self.response_examples:
            return ""

        examples = []
        for ex in self.response_examples:
            example_json = json.dumps(ex.example, indent=2)
            label = ex.type.replace("_", " ").title()
            examples.append(f"**{label}:**\n```json\n{example_json}\n```")
        return "\n\n".join(examples)


# Cached context
_cache: ChatDomainContext | None = None


def _parse_config(data: dict) -> ChatDomainContext:
    """Parse config dict into ChatDomainContext."""
    return ChatDomainContext(
        domain=data.get("domain", "default"),
        display_name=data.get("display_name", "Dashboard"),
        description=data.get("description", ""),
        assistant_role=data.get("assistant_role", "You are a data assistant."),
        search_keywords=data.get("search_keywords", []),
        place_examples=[PlaceExample(**p) for p in data.get("place_examples", [])],
        widgets=[
            WidgetDefinition(
                id=w["id"],
                description=w.get("description", ""),
                default_variable=w.get("default_variable"),
                supports=w.get("supports", [])
            )
            for w in data.get("widgets", [])
        ],
        widget_selection_rules=data.get("widget_selection_rules", []),
        example_queries=[
            QueryExample(question=q["question"], steps=q.get("steps", []))
            for q in data.get("example_queries", [])
        ],
        response_examples=[
            ResponseExample(type=r["type"], example=r["example"])
            for r in data.get("response_examples", [])
        ],
    )


def _get_default_context() -> ChatDomainContext:
    """Return default context when config is not available."""
    return ChatDomainContext(
        domain="default",
        display_name="Data Dashboard",
        description="Data analysis dashboard",
        assistant_role="You are an assistant for a data dashboard. Help users analyze data and update widgets.",
        widgets=[
            WidgetDefinition(id="dc-map", description="Geographic map visualization", supports=["variable", "parentPlace", "childPlaceType", "date"]),
            WidgetDefinition(id="dc-ranking", description="Ranked list of places", supports=["variable", "parentPlace", "childPlaceType"]),
        ],
        place_examples=[PlaceExample(name="USA", dcid="country/USA")],
    )


def get_chat_domain_context(domain: str = None) -> ChatDomainContext:
    """Get the chat domain context.

    Loads from INPUT_DIR (GCS or local). Results are cached.
    The domain parameter is kept for API compatibility but config
    is loaded from a single ai_chat.json file.
    """
    global _cache

    if _cache is not None:
        return _cache

    config_data = _load_config_from_storage()

    if config_data:
        _cache = _parse_config(config_data)
    else:
        logger.warning("Using default chat context")
        _cache = _get_default_context()

    return _cache


def clear_cache():
    """Clear the domain context cache."""
    global _cache
    _cache = None
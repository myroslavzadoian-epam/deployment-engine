/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { getApiRoot } from '../utils/api.js';

// DOM Elements
const aiQueryInput = document.getElementById("ai-query-input");
const aiExamples = document.querySelector(".ai-examples");

// State - prevent duplicate submissions
let isSubmitting = false;

/**
 * Update widget attributes based on AI response configuration
 * @param {string} widgetId - The ID of the widget element to update
 * @param {Object} config - Configuration object with widget attributes
 */
function updateWidgetAttributes(widgetId, config) {
  const widget = document.getElementById(widgetId);
  if (!widget) {
    console.warn(`Widget ${widgetId} not found!`);
    return;
  }

  console.log(`Updating widget ${widgetId} with config:`, config);

  // Map config keys to widget attributes
  const attributeMap = {
    'variable': 'variable',
    'date': 'date',
    'place': 'place',
    'parentPlace': 'parentPlace',
    'childPlaceType': 'childPlaceType'
  };

  // Update widget attributes based on config
  Object.keys(config).forEach(key => {
    if (config[key] !== null && config[key] !== undefined && key !== 'title') {
      const attrName = attributeMap[key] || key;
      const oldValue = widget.getAttribute(attrName);
      widget.setAttribute(attrName, config[key]);
      console.log(`  ${widgetId}.${attrName}: "${oldValue}" -> "${config[key]}"`);
    }
  });

  // Update widget title/label if provided
  if (config.title) {
    updateWidgetTitle(widgetId, widget, config.title);
  }
}

/**
 * Update widget title and related label elements
 * @param {string} widgetId - The ID of the widget
 * @param {HTMLElement} widget - The widget DOM element
 * @param {string} title - The new title text
 */
function updateWidgetTitle(widgetId, widget, title) {
  // Try to find the corresponding label element (widgetId + "Label")
  const labelEl = document.getElementById(widgetId + "Label");
  if (labelEl) {
    console.log(`  Updating label ${widgetId}Label: "${labelEl.textContent}" -> "${title}"`);
    labelEl.textContent = title;
  }

  // For dc-map widget, update the header attribute
  if (widgetId === 'dc-map') {
    widget.setAttribute('header', title);
    console.log(`  Updated dc-map header to: "${title}"`);
  }

  // For dc-ranking widget, update the highestTitle attribute
  if (widgetId === 'dc-ranking') {
    widget.setAttribute('highestTitle', title);
    console.log(`  Updated dc-ranking highestTitle to: "${title}"`);
  }
}

/**
 * Convert markdown-like text to HTML
 * Supports: **bold**, bullet points (• or -), and paragraphs (\n\n)
 * @param {string} text - The markdown text to convert
 * @returns {string} The converted HTML string
 */
function formatMarkdownToHtml(text) {
  if (!text) return '';

  // Escape HTML to prevent XSS
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Convert **bold** to <strong>
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Split into paragraphs by double newlines
  const paragraphs = html.split(/\n\n+/);

  html = paragraphs.map(para => {
    // Check if paragraph contains bullet points
    const lines = para.split('\n');
    const hasBullets = lines.some(line => /^[•\-\*]\s/.test(line.trim()));

    if (hasBullets) {
      return formatBulletList(lines);
    }

    // Regular paragraph
    return `<p>${para.replace(/\n/g, '<br>')}</p>`;
  }).join('');

  return html;
}

/**
 * Format lines containing bullet points into an HTML list
 * @param {string[]} lines - Array of text lines
 * @returns {string} HTML unordered list
 */
function formatBulletList(lines) {
  const listItems = lines.map(line => {
    const trimmed = line.trim();
    if (/^[•\-\*]\s/.test(trimmed)) {
      const content = trimmed.replace(/^[•\-\*]\s+/, '');
      return `<li>${content}</li>`;
    }
    return trimmed ? `<p class="ai-list-header">${trimmed}</p>` : '';
  }).join('');

  return `<ul class="ai-bullet-list">${listItems}</ul>`;
}

/**
 * Render AI response to the container
 * @param {Object} response - The AI response object
 * @param {string} response.summary - Analysis summary text
 * @param {string} response.source - Data source information
 * @param {string[]} response.widgetIds - IDs of widgets to update
 * @param {Object} response.widgetConfigs - Widget configuration objects
 */
function renderAiResponse(response) {
  const container = document.getElementById("ai-response-container");
  container.innerHTML = "";

  // Display summary with Material Design styling
  if (response.summary) {
    const summaryEl = createAnalysisSummary(response);
    container.appendChild(summaryEl);
  }

  // Update widgets if specified
  if (response.widgetIds && response.widgetIds.length > 0) {
    updateWidgets(response);
  }
}

/**
 * Create the analysis summary element
 * @param {Object} response - The AI response object
 * @returns {HTMLElement} The summary DOM element
 */
function createAnalysisSummary(response) {
  const summaryEl = document.createElement("div");
  summaryEl.className = "ai-analysis-result";

  // Add header with icon
  const headerEl = document.createElement("div");
  headerEl.className = "ai-analysis-header";

  const icon = document.createElement("md-icon");
  icon.textContent = "insights";
  headerEl.appendChild(icon);

  const headerText = document.createElement("span");
  headerText.textContent = "AI Analysis";
  headerEl.appendChild(headerText);

  summaryEl.appendChild(headerEl);

  // Add formatted content
  const summaryContent = document.createElement("div");
  summaryContent.className = "ai-analysis-content";
  summaryContent.innerHTML = formatMarkdownToHtml(response.summary);
  summaryEl.appendChild(summaryContent);

  // Add source if present
  if (response.source) {
    const sourceEl = createSourceElement(response.source);
    summaryEl.appendChild(sourceEl);
  }

  return summaryEl;
}

/**
 * Create the source information element
 * @param {string} source - The data source text
 * @returns {HTMLElement} The source DOM element
 */
function createSourceElement(source) {
  const sourceEl = document.createElement("div");
  sourceEl.className = "ai-metric-info";

  const sourceIcon = document.createElement("md-icon");
  sourceIcon.textContent = "database";
  sourceEl.appendChild(sourceIcon);

  const sourceText = document.createElement("span");
  sourceText.textContent = `Source: ${source}`;
  sourceEl.appendChild(sourceText);

  return sourceEl;
}

/**
 * Update widgets based on AI response
 * @param {Object} response - The AI response with widget configurations
 */
function updateWidgets(response) {
  // Remove previous highlights
  document.querySelectorAll('.widget-highlight').forEach(el => {
    el.classList.remove('widget-highlight');
  });

  // Update widget configurations and highlight
  response.widgetIds.forEach(widgetId => {
    const config = response.widgetConfigs ? response.widgetConfigs[widgetId] : null;
    if (config) {
      console.log(`Updating ${widgetId} with config:`, config);
      updateWidgetAttributes(widgetId, config);
    }

    highlightWidget(widgetId, response.widgetIds);
  });
}

/**
 * Highlight a widget and scroll to it if it's the first one
 * @param {string} widgetId - The widget ID to highlight
 * @param {string[]} allWidgetIds - All widget IDs being updated
 */
function highlightWidget(widgetId, allWidgetIds) {
  const widget = document.getElementById(widgetId);
  if (!widget) return;

  const card = widget.closest('.kpi-card') || widget.closest('.widget-container') || widget.parentElement;
  if (card) {
    card.classList.add('widget-highlight');

    // Scroll to first updated widget
    if (allWidgetIds.indexOf(widgetId) === 0) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

/**
 * Show loading state in the response container
 */
function showLoadingState() {
  const responseContainer = document.getElementById("ai-response-container");
  responseContainer.innerHTML = `
    <div class="ai-loading">
      <div class="ai-loading-spinner"></div>
      <span>Generating response...</span>
    </div>
  `;
}

/**
 * Show error state in the response container
 * @param {string} errorMessage - The error message to display
 */
function showErrorState(errorMessage) {
  const responseContainer = document.getElementById("ai-response-container");
  responseContainer.innerHTML = `<p style="color: red;">Error: ${errorMessage}</p>`;
}

/**
 * Submit AI query to the backend
 */
async function submitAiQuery() {
  const apiRoot = getApiRoot();
  const query = aiQueryInput.value;

  if (!query) return;

  // Prevent duplicate submissions
  if (isSubmitting) {
    console.log("Query already in progress, skipping duplicate submission");
    return;
  }

  isSubmitting = true;
  showLoadingState();

  try {
    // Use domain-specific chat endpoint for education
    const response = await fetch(`${apiRoot}/api/ai/chat/education`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        context: {
          parentPlace: 'country/USA',
          childType: 'State',
        }
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    renderAiResponse(result);
  } catch (error) {
    showErrorState(error.message);
    console.error("Error fetching AI response:", error);
  } finally {
    isSubmitting = false;
  }
}

// Query input event handlers
aiQueryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    submitAiQuery();
  }
});

// Ask button click handler
document.getElementById("ai-ask-button").addEventListener("click", () => {
  submitAiQuery();
});

// Suggestions visibility handlers
aiQueryInput.addEventListener("focus", () => {
  aiExamples.classList.add("visible");
});

aiQueryInput.addEventListener("blur", (e) => {
  // Delay hiding to allow clicking on example chips
  setTimeout(() => {
    // Only hide if not clicking on an example chip or link
    if (!e.relatedTarget ||
        (!e.relatedTarget.classList.contains("example-chip") &&
         !e.relatedTarget.classList.contains("example-link"))) {
      aiExamples.classList.remove("visible");
    }
  }, 200);
});

// Example chips click handler
document.querySelectorAll(".example-chip, .example-link").forEach(chip => {
  chip.addEventListener("click", (e) => {
    e.preventDefault();
    const query = chip.getAttribute("data-query");
    aiQueryInput.value = query;

    // Hide suggestions after selection
    aiExamples.classList.remove("visible");

    // Focus on the text field
    setTimeout(() => aiQueryInput.focus(), 0);
  });
});

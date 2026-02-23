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

/**
 * Forecast Widget Component
 *
 * A standalone JavaScript component for rendering forecast data
 * from the /api/ai/insights/<domain> endpoint.
 *
 * Usage:
 *   <link href="forecast-widget.css" rel="stylesheet">
 *   <div id="forecast-container" data-domain="education"></div>
 *   <script type="module">
 *     import { initForecastWidget } from './forecast-widget.js';
 *     initForecastWidget('forecast-container');
 *   </script>
 */

import { getApiRoot } from '../utils/api.js';

// Google Material Design colors
const COLORS = {
  blue: '#1A73E8',
};

// SVG Icons
const SPARKLE_ICON = `<svg class="forecast-sparkle-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${COLORS.blue}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path>
  <path d="M20 3v4"></path>
  <path d="M22 5h-4"></path>
  <path d="M4 17v2"></path>
  <path d="M5 18H3"></path>
</svg>`;

/**
 * Render loading state HTML
 * @returns {string} Loading state HTML string
 */
function renderLoading() {
  return `
    <div class="forecast-widget">
      <div class="forecast-loading">
        <div class="forecast-loading-spinner"></div>
        <span>Loading forecast data...</span>
      </div>
    </div>
  `;
}

/**
 * Render error state HTML
 * @param {string} message - Error message to display
 * @returns {string} Error state HTML string
 */
function renderError(message) {
  return `
    <div class="forecast-widget">
      <div class="forecast-error">
        <p>Unable to load forecast data: ${message}</p>
      </div>
    </div>
  `;
}

/**
 * Determine if a value string represents a positive or negative number
 * @param {string} valueStr - Value string to check
 * @returns {boolean} True if positive, false if negative
 */
function isPositiveValue(valueStr) {
  if (!valueStr) return true;
  // Check if starts with minus or contains negative number
  const cleaned = valueStr.toString().trim();
  return !cleaned.startsWith('-');
}

/**
 * Get the appropriate CSS class for a value (positive = green, negative = red)
 * @param {string} valueStr - Value string to check
 * @returns {string} CSS class name
 */
function getValueClass(valueStr) {
  return isPositiveValue(valueStr) ? 'forecast-positive' : 'forecast-negative';
}

/**
 * Render the forecast widget HTML
 * @param {Object} data - API response data containing forecast
 * @returns {string} Forecast widget HTML string
 */
function renderForecast(data) {
  const forecast = data.forecast;

  if (!forecast) {
    return renderError('No forecast data available');
  }

  // Determine growth class based on value
  const growthClass = getValueClass(forecast.projected_growth);

  // Build top growth regions HTML
  const topRegionsHtml = forecast.top_growth_regions
    .map((r, i) => `${i + 1}. ${r.name} (<span class="${getValueClass(r.growth)}">${r.growth}</span>)`)
    .join(' • ');

  // Build declining regions HTML
  const decliningRegionsHtml = forecast.declining_regions
    .map((r, i) => `${i + 1}. ${r.name} (<span class="${getValueClass(r.decline)}">${r.decline}</span>)`)
    .join(' • ');

  // Build suggested actions HTML
  const actionsHtml = forecast.suggested_actions.map(action => `
    <div class="forecast-suggested-action">
      ${SPARKLE_ICON}
      <div class="forecast-action-content">
        <p class="forecast-action-label">Suggested Action:</p>
        <p class="forecast-action-text">${action.text}</p>
        <p class="forecast-action-timestamp">Last updated: ${action.updated_at}</p>
      </div>
    </div>
  `).join('');

  return `
    <div class="forecast-widget">
      <div class="forecast-widget-header">
        <h6 class="forecast-widget-title">Short Forecast Summary</h6>
        <p class="forecast-widget-subtitle">Based on Uploaded Applicant Data + Data Commons Trends</p>
      </div>

      <div class="forecast-content-box">
        <div class="forecast-item">
          <p class="forecast-item-label">• Next year projected applicant growth: <span class="${growthClass}">${forecast.projected_growth}</span></p>
        </div>
        <div class="forecast-item">
          <p class="forecast-item-label">• Top ${forecast.top_growth_regions.length} growth regions:</p>
          <p class="forecast-item-value">${topRegionsHtml}</p>
        </div>
        <div class="forecast-item">
          <p class="forecast-item-label">• ${forecast.declining_regions.length} declining regions:</p>
          <p class="forecast-item-value">${decliningRegionsHtml}</p>
        </div>
        <div class="forecast-item">
          <p class="forecast-item-label">• Diversity shift prediction:</p>
          <p class="forecast-item-value">${forecast.diversity_prediction.description}</p>
        </div>
      </div>

      ${actionsHtml}
    </div>
  `;
}

/**
 * Fetch forecast data from API
 * @param {string} domain - Domain identifier (e.g., 'education')
 * @returns {Promise<Object>} API response with forecast data
 */
async function fetchForecastData(domain) {
  const apiRoot = getApiRoot();
  const response = await fetch(`${apiRoot}/api/ai/insights/${domain}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Initialize the forecast widget with pre-fetched data
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Pre-fetched API response data
 */
export function initForecastWidgetWithData(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Forecast Widget: Container with id "${containerId}" not found`);
    return;
  }

  container.innerHTML = renderForecast(data);
}

/**
 * Show loading state for the forecast widget
 * @param {string} containerId - ID of the container element
 */
export function showForecastLoading(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = renderLoading();
  }
}

/**
 * Show error state for the forecast widget
 * @param {string} containerId - ID of the container element
 * @param {string} message - Error message
 */
export function showForecastError(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = renderError(message);
  }
}

/**
 * Initialize the forecast widget (fetches its own data)
 * @param {string} containerId - ID of the container element
 * @param {Object} options - Configuration options
 * @param {string} options.domain - Domain identifier (default: from data attribute or 'education')
 */
export async function initForecastWidget(containerId, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Forecast Widget: Container with id "${containerId}" not found`);
    return;
  }

  // Get domain from options or data attribute
  const domain = options.domain || container.dataset.domain || 'education';

  // Show loading state
  container.innerHTML = renderLoading();

  try {
    // Fetch data
    const data = await fetchForecastData(domain);

    // Render widget
    container.innerHTML = renderForecast(data);
  } catch (error) {
    console.error('Forecast Widget: Failed to fetch data', error);
    container.innerHTML = renderError(error.message);
  }
}

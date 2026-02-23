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
 * Gemini AI Insights Widget Component
 *
 * A standalone JavaScript component for rendering AI-generated insights
 * from the /api/ai/insights/<domain> endpoint.
 *
 * Usage:
 *   <link href="ai-insights-widget.css" rel="stylesheet">
 *   <div id="ai-insights-container" data-domain="education"></div>
 *   <script type="module">
 *     import { initAiInsightsWidget } from './ai-insights-widget.js';
 *     initAiInsightsWidget('ai-insights-container');
 *   </script>
 */

import { getApiRoot } from '../utils/api.js';

// Google Material Design colors
const COLORS = {
  blue: '#1A73E8',
  blueBg: '#E8F0FE',
  green: '#34A853',
  greenBg: '#E6F4EA',
  red: '#EA4335',
  redBg: '#FDECEA',
  yellow: '#F9AB00',
  yellowBg: '#FEF7E0',
  orange: '#FA903E',
  orangeBg: '#FEF0E6',
  purple: '#9334E6',
  purpleBg: '#F3E8FD',
  teal: '#00ACC1',
  tealBg: '#E0F7FA',
  gray: '#5F6368',
  grayLight: '#9AA0A6',
  grayBg: '#F1F3F4',
  darkGray: '#202124',
  lightGray: '#E8EAED',
  white: '#FFFFFF',
};

// Icon SVG map - maps icon names from AI response to SVG code
const ICON_SVG_MAP = {
  trending_up: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline><polyline points="16 7 22 7 22 13"></polyline></svg>`,
  trending_down: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"></polyline><polyline points="16 17 22 17 22 11"></polyline></svg>`,
  users: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
  warning: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
  diversity: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="4"></circle><line x1="21.17" y1="8" x2="12" y2="8"></line><line x1="3.95" y1="6.06" x2="8.54" y2="14"></line><line x1="10.88" y1="21.94" x2="15.46" y2="14"></line></svg>`,
  dollar: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>`,
  clock: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
  lightbulb: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"></path><path d="M9 18h6"></path><path d="M10 22h4"></path></svg>`,
  chart: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>`,
  target: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
  info: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`,
};

// List of icon names for random selection
const ICON_NAMES = Object.keys(ICON_SVG_MAP);

/**
 * Get icon SVG by name
 * @param {string} iconName - Icon name from ICON_SVG_MAP
 * @returns {string} SVG markup
 */
function getIconSvg(iconName) {
  return ICON_SVG_MAP[iconName] || ICON_SVG_MAP.info;
}

/**
 * Get a random icon name from the available icons
 * @returns {string} Random icon name
 */
function getRandomIconName() {
  return ICON_NAMES[Math.floor(Math.random() * ICON_NAMES.length)];
}

/**
 * Get color scheme based on priority for fallback styling
 * @param {string} priority - Priority level
 * @returns {Object} Object with color and bgColor
 */
function getColorSchemeForPriority(priority) {
  switch (priority) {
    case 'critical':
      return { color: COLORS.red, bgColor: COLORS.redBg };
    case 'high':
      return { color: COLORS.orange, bgColor: COLORS.orangeBg };
    case 'moderate':
    case 'medium':
      return { color: COLORS.yellow, bgColor: COLORS.yellowBg };
    case 'low':
      return { color: COLORS.grayLight, bgColor: COLORS.grayBg };
    case 'monitored':
      return { color: COLORS.blue, bgColor: COLORS.blueBg };
    default:
      return { color: COLORS.blue, bgColor: COLORS.blueBg };
  }
}

/**
 * Get badge text based on priority
 * @param {string} priority - Priority level
 * @returns {string} Badge text
 */
function getBadgeTextForPriority(priority) {
  switch (priority) {
    case 'critical': return 'Critical';
    case 'high': return 'High';
    case 'moderate':
    case 'medium': return 'Moderate';
    case 'low': return 'Low';
    case 'monitored': return 'Monitored';
    default: return 'Info';
  }
}

/**
 * Format insight type to display title
 * @param {string} type - Insight type (e.g., 'emerging_opportunity')
 * @returns {string} Formatted title (e.g., 'Emerging Opportunity')
 */
function formatTypeToTitle(type) {
  if (!type) return 'Insight';
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get style configuration for an insight
 * Uses AI-provided style, with random icon fallback
 * @param {Object} insight - Insight data object
 * @returns {Object} Style configuration with iconBg, iconColor, iconSvg, title, badgeText, badgeColor
 */
function getInsightStyle(insight) {
  // If AI provided style, use it (with random icon fallback if icon_name missing)
  if (insight.style) {
    const style = insight.style;
    const iconName = style.icon_name || getRandomIconName();
    const colorScheme = getColorSchemeForPriority(insight.priority);
    
    return {
      iconBg: style.icon_bg_color || colorScheme.bgColor,
      iconColor: style.icon_color || colorScheme.color,
      iconSvg: getIconSvg(iconName),
      title: style.display_title || formatTypeToTitle(insight.type),
      badgeText: style.badge_text || getBadgeTextForPriority(insight.priority),
      badgeColor: style.badge_color || colorScheme.color,
    };
  }
  
  // Fallback: generate style from priority with random icon
  const colorScheme = getColorSchemeForPriority(insight.priority);
  const randomIconName = getRandomIconName();
  
  return {
    iconBg: colorScheme.bgColor,
    iconColor: colorScheme.color,
    iconSvg: getIconSvg(randomIconName),
    title: formatTypeToTitle(insight.type),
    badgeText: getBadgeTextForPriority(insight.priority),
    badgeColor: colorScheme.color,
  };
}

// Widget state
let widgetState = {
  domain: null,
  containerId: null,
  refreshFn: null,
  insights: [] // Store insights for modal access
};

/**
 * Create and append the modal container to the DOM if it doesn't exist
 */
function ensureModalContainer() {
  if (!document.getElementById('gemini-insight-modal')) {
    const modalHtml = `
      <div id="gemini-insight-modal" class="gemini-modal-overlay" style="display: none;">
        <div class="gemini-modal-container">
          <div class="gemini-modal-header">
            <div class="gemini-modal-icon"></div>
            <div class="gemini-modal-header-content">
              <h3 class="gemini-modal-title"></h3>
              <span class="gemini-modal-badge"></span>
            </div>
            <button class="gemini-modal-close" aria-label="Close modal">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="gemini-modal-body">
            <p class="gemini-modal-description"></p>
          </div>
          <div class="gemini-modal-footer">
            <button class="gemini-modal-btn-secondary gemini-modal-close-btn">Close</button>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Setup modal event listeners
    const modal = document.getElementById('gemini-insight-modal');
    const closeBtn = modal.querySelector('.gemini-modal-close');
    const closeBtnSecondary = modal.querySelector('.gemini-modal-close-btn');
    
    // Close on X button click
    closeBtn.addEventListener('click', closeInsightModal);
    closeBtnSecondary.addEventListener('click', closeInsightModal);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeInsightModal();
      }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display !== 'none') {
        closeInsightModal();
      }
    });
  }
}

/**
 * Open the insight modal with full details
 * @param {number} index - Index of the insight in widgetState.insights
 */
function openInsightModal(index) {
  const insight = widgetState.insights[index];
  if (!insight) return;
  
  const style = getInsightStyle(insight);
  
  ensureModalContainer();
  
  const modal = document.getElementById('gemini-insight-modal');
  const iconEl = modal.querySelector('.gemini-modal-icon');
  const titleEl = modal.querySelector('.gemini-modal-title');
  const badgeEl = modal.querySelector('.gemini-modal-badge');
  const descriptionEl = modal.querySelector('.gemini-modal-description');
  
  // Set icon
  iconEl.innerHTML = style.iconSvg;
  iconEl.style.background = style.iconBg;
  iconEl.style.color = style.iconColor;
  
  // Set title
  titleEl.textContent = style.title;
  
  // Set badge
  badgeEl.textContent = style.badgeText;
  badgeEl.style.color = style.badgeColor;
  badgeEl.style.borderColor = style.badgeColor;
  
  // Set full description
  descriptionEl.textContent = insight.description || 'No additional details available.';
  
  // Show modal with animation
  modal.style.display = 'flex';
  requestAnimationFrame(() => {
    modal.classList.add('gemini-modal-visible');
  });
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden';
}

/**
 * Close the insight modal
 */
function closeInsightModal() {
  const modal = document.getElementById('gemini-insight-modal');
  if (!modal) return;
  
  modal.classList.remove('gemini-modal-visible');
  
  // Wait for animation to finish
  setTimeout(() => {
    modal.style.display = 'none';
  }, 200);
  
  // Restore body scroll
  document.body.style.overflow = '';
}

/**
 * Setup click handlers for insight cards using event delegation
 * @param {string} containerId - ID of the insights container
 */
function setupInsightCardClickHandlers(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  // Use event delegation - attach one listener to the container
  container.addEventListener('click', (e) => {
    const button = e.target.closest('.gemini-insight-action-btn');
    if (!button) return;
    
    // Find the card and its index
    const card = button.closest('.gemini-insight-card');
    if (!card) return;
    
    const cardsContainer = container.querySelector('.gemini-insights-cards-container');
    if (!cardsContainer) return;
    
    const cards = Array.from(cardsContainer.querySelectorAll('.gemini-insight-card'));
    const index = cards.indexOf(card);
    
    if (index !== -1) {
      openInsightModal(index);
    }
  });
}

/**
 * Render the loading state HTML
 * @returns {string} Loading state HTML string
 */
function renderLoading() {
  return `
    <div class="gemini-insights-widget">
      <div class="gemini-insights-loading">
        <div class="gemini-insights-spinner"></div>
        <span>Generating AI insights...</span>
      </div>
    </div>
  `;
}

/**
 * Render an error state HTML
 * @param {string} message - Error message to display
 * @returns {string} Error state HTML string
 */
function renderError(message) {
  return `
    <div class="gemini-insights-widget">
      <div class="gemini-insights-error">
        <p>Unable to load insights: ${message}</p>
        <button class="gemini-insights-error-btn" onclick="window.aiInsightsWidget.refresh()">
          Try Again
        </button>
      </div>
    </div>
  `;
}

/**
 * Get badge information for an insight
 * @param {Object} insight - Insight data object
 * @returns {Object} Badge info with text and color properties
 */
function getBadgeInfo(insight) {
  const style = getInsightStyle(insight);
  return { text: style.badgeText, color: style.badgeColor };
}

/**
 * Render a single insight card
 * @param {Object} insight - Insight data object
 * @returns {string} Insight card HTML string
 */
function renderInsightCard(insight) {
  const style = getInsightStyle(insight);

  // Truncate description if too long
  let description = insight.description || '';
  if (description.length > 100) {
    description = description.substring(0, 97) + '...';
  }

  return `
    <div class="gemini-insight-card" style="--card-accent-color: ${style.badgeColor}">
      <div class="gemini-insight-icon" style="background: ${style.iconBg}; color: ${style.iconColor}">
        ${style.iconSvg}
      </div>
      <h4 class="gemini-insight-card-title">${style.title}</h4>
      <span class="gemini-insight-badge" style="color: ${style.badgeColor}; border-color: ${style.badgeColor}">
        ${style.badgeText}
      </span>
      <p class="gemini-insight-description">${description}</p>
      <button class="gemini-insight-action-btn">Open More</button>
    </div>
  `;
}

/**
 * Render the complete Gemini AI Insights Panel
 * @param {Object} data - API response data with insights array
 * @returns {string} Complete widget HTML string
 */
function renderInsights(data) {
  const insights = data.insights || [];
  
  // Store insights in widget state for modal access
  widgetState.insights = insights;

  if (insights.length === 0) {
    return `
      <div class="gemini-insights-widget">
        <div class="gemini-insights-header">
          <h3 class="gemini-insights-title">Gemini AI Insights Panel</h3>
        </div>
        <div class="gemini-insights-empty">
          <p>No insights available at this time.</p>
        </div>
      </div>
    `;
  }

  const insightCardsHtml = insights.map(insight => renderInsightCard(insight)).join('');

  return `
    <div class="gemini-insights-widget">
      <div class="gemini-insights-header">
        <span class="gemini-logo-text">Gemini</span>
        <h3 class="gemini-insights-title">Gemini AI Insights Panel</h3>
      </div>

      <div class="gemini-insights-cards-wrapper">
        <div class="gemini-insights-cards-container" id="gemini-cards-container">
          ${insightCardsHtml}
        </div>
        <div class="gemini-insights-scrollbar">
          <div class="gemini-insights-scrollbar-thumb"></div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Setup scroll tracking for custom scrollbar
 */
function setupScrollTracking() {
  const container = document.getElementById('gemini-cards-container');
  const scrollbar = document.querySelector('.gemini-insights-scrollbar');
  const thumb = document.querySelector('.gemini-insights-scrollbar-thumb');

  if (!container || !scrollbar || !thumb) return;

  // Calculate thumb width based on visible content ratio
  const updateThumbSize = () => {
    const ratio = container.clientWidth / container.scrollWidth;
    const thumbWidthPercent = Math.max(20, ratio * 100);
    thumb.style.width = `${thumbWidthPercent}%`;
    return thumbWidthPercent;
  };

  // Update thumb position based on scroll
  const updateThumbPosition = () => {
    const scrollableWidth = container.scrollWidth - container.clientWidth;
    if (scrollableWidth <= 0) {
      thumb.style.left = '0%';
      return;
    }
    const scrollPercent = container.scrollLeft / scrollableWidth;
    const thumbWidth = parseFloat(thumb.style.width) || 20;
    const maxLeftPercent = 100 - thumbWidth;
    thumb.style.left = `${scrollPercent * maxLeftPercent}%`;
  };

  // Initial setup
  updateThumbSize();
  updateThumbPosition();

  // Track container scroll
  container.addEventListener('scroll', updateThumbPosition);

  // Click on scrollbar track to scroll
  scrollbar.addEventListener('click', (e) => {
    if (e.target === thumb) return;
    const rect = scrollbar.getBoundingClientRect();
    const clickPercent = (e.clientX - rect.left) / rect.width;
    const scrollableWidth = container.scrollWidth - container.clientWidth;
    container.scrollLeft = clickPercent * scrollableWidth;
  });

  // Drag thumb to scroll
  let isDragging = false;
  let startX = 0;
  let startScrollLeft = 0;

  thumb.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX;
    startScrollLeft = container.scrollLeft;
    thumb.style.transition = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const rect = scrollbar.getBoundingClientRect();
    const deltaX = e.clientX - startX;
    const scrollableWidth = container.scrollWidth - container.clientWidth;
    const trackWidth = rect.width;
    const thumbWidth = thumb.offsetWidth;
    const scrollRatio = scrollableWidth / (trackWidth - thumbWidth);
    container.scrollLeft = startScrollLeft + (deltaX * scrollRatio);
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      thumb.style.transition = 'left 0.1s ease-out';
    }
  });

  // Update on window resize
  window.addEventListener('resize', () => {
    updateThumbSize();
    updateThumbPosition();
  });
}

/**
 * Fetch insights from the API
 * @param {string} domain - Domain identifier (e.g., 'education')
 * @param {boolean} forceRefresh - Whether to force refresh cached data
 * @returns {Promise<Object>} API response with insights data
 */
async function fetchInsights(domain, forceRefresh = false) {
  const apiRoot = getApiRoot();
  const url = `${apiRoot}/api/ai/insights/${domain}${forceRefresh ? '/refresh' : ''}`;

  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Load and render insights
 * @param {HTMLElement} container - Container element to render into
 * @param {string} domain - Domain identifier
 * @param {boolean} forceRefresh - Whether to force refresh
 */
async function loadInsights(container, domain, forceRefresh = false) {
  container.innerHTML = renderLoading();

  try {
    const data = await fetchInsights(domain, forceRefresh);
    container.innerHTML = renderInsights(data);
    // Setup scroll tracking after render
    setTimeout(setupScrollTracking, 100);
    // Setup click handlers using event delegation
    setupInsightCardClickHandlers(container.id);
  } catch (error) {
    console.error('Gemini AI Insights error:', error);
    container.innerHTML = renderError(error.message || 'Failed to load insights');
  }
}

/**
 * Initialize the Gemini AI Insights widget with pre-fetched data
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Pre-fetched API response data
 * @param {Object} options - Configuration options
 * @param {string} options.domain - Domain identifier (for refresh functionality)
 */
export function initAiInsightsWidgetWithData(containerId, data, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Gemini AI Insights: Container #${containerId} not found`);
    return;
  }

  const domain = options.domain || container.dataset.domain || 'education';

  // Store widget state
  widgetState.domain = domain;
  widgetState.containerId = containerId;
  widgetState.refreshFn = () => loadInsights(container, domain, true);

  // Expose widget API globally for error retry button
  window.aiInsightsWidget = {
    domain,
    containerId,
    refresh: widgetState.refreshFn
  };

  // Render with provided data
  container.innerHTML = renderInsights(data);
  // Setup scroll tracking after render
  setTimeout(setupScrollTracking, 100);
  // Setup click handlers using event delegation (no need for timeout)
  setupInsightCardClickHandlers(containerId);
}

/**
 * Show loading state for the AI insights widget
 * @param {string} containerId - ID of the container element
 */
export function showAiInsightsLoading(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = renderLoading();
  }
}

/**
 * Show error state for the AI insights widget
 * @param {string} containerId - ID of the container element
 * @param {string} message - Error message
 */
export function showAiInsightsError(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = renderError(message);
  }
}

/**
 * Initialize the Gemini AI Insights widget (fetches its own data)
 * @param {string} containerId - ID of the container element
 * @param {Object} options - Configuration options
 * @param {string} options.domain - Domain identifier (default: from data attribute or 'education')
 * @param {number} options.autoRefreshMinutes - Auto-refresh interval in minutes
 */
export async function initAiInsightsWidget(containerId, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Gemini AI Insights: Container #${containerId} not found`);
    return;
  }

  const domain = options.domain || container.dataset.domain || 'education';

  // Store widget state
  widgetState.domain = domain;
  widgetState.containerId = containerId;
  widgetState.refreshFn = () => loadInsights(container, domain, true);

  // Expose widget API globally for error retry button
  window.aiInsightsWidget = {
    domain,
    containerId,
    refresh: widgetState.refreshFn
  };

  // Initial load
  await loadInsights(container, domain);

  // Auto-refresh if configured
  if (options.autoRefreshMinutes) {
    setInterval(() => loadInsights(container, domain), options.autoRefreshMinutes * 60 * 1000);
  }
}

/**
 * Refresh the currently initialized widget
 */
export function refreshAiInsightsWidget() {
  if (widgetState.refreshFn) {
    widgetState.refreshFn();
  }
}

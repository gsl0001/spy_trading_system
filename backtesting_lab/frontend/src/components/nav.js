/**
 * Navigation Component — Sidebar with routing and system status.
 */
import { createElement, $ } from '../utils.js';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '◈', section: 'TRADING' },
  { id: 'backtest', label: 'Backtest Lab', icon: '⟐', section: 'TRADING' },
  { id: 'config', label: 'Configuration', icon: '⚙', section: 'SYSTEM' },
  { id: 'reports', label: 'Reports', icon: '◩', section: 'SYSTEM' },
  { id: 'deployment', label: 'Deployment', icon: '▶', section: 'SYSTEM' },
];

export function renderNav(container, activePage, onNavigate) {
  // Group items by section
  const sections = {};
  NAV_ITEMS.forEach(item => {
    if (!sections[item.section]) sections[item.section] = [];
    sections[item.section].push(item);
  });

  container.innerHTML = `
    <div class="sidebar-brand">
      <div class="sidebar-brand-icon">Q</div>
      <div class="sidebar-brand-text">
        <h1>Quant<span>OS</span></h1>
        <p>SPY Trading Engine</p>
      </div>
    </div>
    <nav class="sidebar-nav">
      ${Object.entries(sections).map(([section, items]) => `
        <div class="sidebar-section-label">${section}</div>
        ${items.map(item => `
          <a class="nav-item ${item.id === activePage ? 'active' : ''}" data-page="${item.id}" id="nav-${item.id}">
            <span class="nav-icon">${item.icon}</span>
            <span>${item.label}</span>
          </a>
        `).join('')}
      `).join('')}
    </nav>
    <div class="sidebar-status">
      <div class="status-card">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <div class="status-indicator paper" id="nav-status-dot"></div>
          <div>
            <div style="font-size: 12px; font-weight: 600;" id="nav-status-text">Paper Mode</div>
            <div style="font-size: 10px; color: var(--text-tertiary);" id="nav-status-sub">Dry Run Active</div>
          </div>
        </div>
        <div id="nav-active-strategy" style="display: none; padding-top: 8px; border-top: 1px solid var(--border-subtle);">
          <div style="font-size: 9px; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.05em; margin-bottom: 4px;">Active Strategy</div>
          <div style="font-size: 11px; color: var(--accent-green); font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" id="nav-strat-name">None</div>
        </div>
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary); margin-top: 8px;" id="nav-version">v5.0</div>
      </div>
    </div>
  `;

  // Bind click handlers
  container.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const page = el.dataset.page;
      onNavigate(page);
    });
  });
}

export function updateNavStatus(status) {
  const dot = $('#nav-status-dot');
  const text = $('#nav-status-text');
  const sub = $('#nav-status-sub');
  const stratContainer = $('#nav-active-strategy');
  const stratName = $('#nav-strat-name');
  if (!dot) return;

  dot.className = 'status-indicator';
  if (status.is_running) {
    dot.classList.add('live');
    text.textContent = status.mode === 'live' ? 'LIVE' : 'Paper Trading';
    sub.textContent = `Running • ${status.trades_executed || 0} trades`;
    
    // Highlight strategy
    if (stratContainer && stratName) {
      stratContainer.style.display = 'block';
      const activeStrats = status.active_positions && status.active_positions.length > 0 
        ? [...new Set(status.active_positions.map(p => p.strategy))].join(', ')
        : 'Awaiting Signal...';
      stratName.textContent = activeStrats;
    }
  } else {
    dot.classList.add(status.dry_run ? 'paper' : 'offline');
    text.textContent = status.dry_run ? 'Paper Mode' : 'Offline';
    sub.textContent = 'Dry Run Active';
    if (stratContainer) stratContainer.style.display = 'none';
  }
}

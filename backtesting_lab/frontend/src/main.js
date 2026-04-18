/**
 * QuantOS — Main Application Entry Point
 * Handles routing, layout, and WebSocket connection.
 */
import './index.css';
import { renderNav, updateNavStatus } from './components/nav.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderBacktest } from './pages/backtest.js';
import { renderConfig } from './pages/config.js';
import { renderReports } from './pages/reports.js';
import { renderDeployment, destroyDeployment } from './pages/deployment.js';
import { api, ws } from './api.js';

// ── Global State ──
let currentPage = 'dashboard';
let previousPage = null;

// ── Page Registry ──
const PAGES = {
  dashboard: { render: renderDashboard, title: 'Dashboard' },
  backtest: { render: renderBacktest, title: 'Backtest Lab' },
  config: { render: renderConfig, title: 'Configuration' },
  reports: { render: renderReports, title: 'Reports' },
  deployment: { render: renderDeployment, title: 'Deployment' },
};

// ── Initialize App ──
function init() {
  const app = document.getElementById('app');
  if (!app) return;

  // Build layout
  app.innerHTML = `
    <div class="app-layout">
      <aside class="sidebar" id="sidebar"></aside>
      <main class="main-content" id="main-content"></main>
    </div>
  `;

  // Read initial route from hash
  const hash = window.location.hash.replace('#', '') || 'dashboard';
  currentPage = PAGES[hash] ? hash : 'dashboard';

  // Render nav
  renderNav(document.getElementById('sidebar'), currentPage, navigateTo);

  // Render initial page
  renderPage(currentPage);

  // Hash routing
  window.addEventListener('hashchange', () => {
    const page = window.location.hash.replace('#', '') || 'dashboard';
    if (PAGES[page] && page !== currentPage) {
      navigateTo(page);
    }
  });

  // Connect WebSocket
  ws.connect();

  // Listen for status updates
  ws.on('heartbeat', (data) => {
    updateNavStatus(data);
  });

  // Periodic status poll (fallback if WS not connected)
  setInterval(async () => {
    try {
      const status = await api.liveStatus();
      updateNavStatus(status);
    } catch (e) { /* server might be down */ }
  }, 10000);
}

// ── Navigation ──
function navigateTo(page) {
  if (!PAGES[page] || page === currentPage) return;

  // Cleanup previous page
  if (previousPage === 'deployment') {
    destroyDeployment();
  }

  previousPage = currentPage;
  currentPage = page;

  // Update URL hash
  window.location.hash = page;

  // Update nav active state
  renderNav(document.getElementById('sidebar'), currentPage, navigateTo);

  // Render page
  renderPage(page);

  // Update document title
  document.title = `${PAGES[page].title} — QuantOS`;
}

async function renderPage(page) {
  const mainContent = document.getElementById('main-content');
  if (!mainContent || !PAGES[page]) return;

  // Clear and render
  mainContent.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 50vh;"><div class="spinner" style="width: 32px; height: 32px;"></div></div>';

  try {
    await PAGES[page].render(mainContent);
  } catch (err) {
    console.error(`Failed to render page "${page}":`, err);
    mainContent.innerHTML = `
      <div class="empty-state" style="margin-top: 20vh;">
        <div class="empty-state-icon">⚠️</div>
        <h3>Connection Error</h3>
        <p>Could not connect to the server. Make sure the FastAPI backend is running on port 8000.</p>
        <button class="btn btn-primary" style="margin-top: 16px;" onclick="location.reload()">Retry</button>
      </div>
    `;
  }
}

// ── Boot ──
document.addEventListener('DOMContentLoaded', init);

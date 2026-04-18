/**
 * Deployment Page — System control center for autonomous trading.
 */
import { api } from '../api.js';
import { timeAgo, toast } from '../utils.js';

let statusInterval = null;

export async function renderDeployment(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <div>
          <div class="page-badge">▶ COMMAND CENTER</div>
          <h2 class="page-title">Deployment <span>Control</span></h2>
          <p class="page-subtitle">Start, stop, and monitor the autonomous trading engine</p>
        </div>
      </div>

      <div class="grid-2" style="gap: var(--space-lg);">
        <!-- Left: Controls -->
        <div>
          <!-- Status Card -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Engine Status</span></div>
            <div id="dep-status-body"></div>
          </div>

          <!-- Control Buttons -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Controls</span></div>
            <div style="display: flex; flex-direction: column; gap: var(--space-md);">
              <div style="display: flex; gap: 12px;">
                <button class="btn btn-success" id="dep-start-paper" style="flex: 1;">▶ Start Paper</button>
                <button class="btn btn-primary" id="dep-start-live" style="flex: 1;">▶ Start Live</button>
              </div>
              <button class="btn btn-ghost btn-full" id="dep-stop">⏹ Stop Engine</button>
            </div>
          </div>

          <!-- Emergency -->
          <div class="card" style="border-color: rgba(255, 69, 58, 0.2); background: rgba(255, 69, 58, 0.02);">
            <div class="card-header"><span class="card-label" style="color: var(--accent-red);">Emergency</span></div>
            <p style="font-size: 12px; color: var(--text-tertiary); margin-bottom: var(--space-md);">
              Immediately close all positions and halt the trading engine. This action cannot be undone.
            </p>
            <button class="emergency-btn" id="dep-emergency" style="width: 100%;">⚡ EMERGENCY STOP</button>
          </div>
        </div>

        <!-- Right: Monitoring -->
        <div>
          <!-- Live Metrics -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Live Metrics</span></div>
            <div id="dep-metrics"></div>
          </div>

          <!-- Active Positions -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Active Positions</span></div>
            <div id="dep-positions"></div>
          </div>

          <!-- Recent Errors -->
          <div class="card">
            <div class="card-header"><span class="card-label">Recent Errors</span></div>
            <div id="dep-errors"></div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Bind buttons
  document.getElementById('dep-start-paper')?.addEventListener('click', () => startEngine('paper'));
  document.getElementById('dep-start-live')?.addEventListener('click', () => startEngine('live'));
  document.getElementById('dep-stop')?.addEventListener('click', stopEngine);
  document.getElementById('dep-emergency')?.addEventListener('click', emergencyStop);

  // Initial status
  await refreshStatus();

  // Auto-refresh every 3 seconds
  if (statusInterval) clearInterval(statusInterval);
  statusInterval = setInterval(refreshStatus, 3000);
}

async function refreshStatus() {
  try {
    const status = await api.liveStatus();
    updateStatusUI(status);
  } catch (e) {
    // Server might be down
    updateStatusUI({ is_running: false, mode: 'unknown', dry_run: true, uptime_seconds: 0 });
  }
}

function updateStatusUI(s) {
  // Status body
  const statusEl = document.getElementById('dep-status-body');
  if (statusEl) {
    const statusColor = s.is_running ? 'var(--accent-green)' : 'var(--accent-red)';
    const statusText = s.is_running ? 'RUNNING' : 'STOPPED';
    const modeText = s.is_running ? (s.mode === 'live' ? 'LIVE' : 'PAPER') : 'IDLE';

    statusEl.innerHTML = `
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: var(--space-lg);">
        <div style="width: 48px; height: 48px; border-radius: 50%; background: ${statusColor}15; display: flex; align-items: center; justify-content: center;">
          <div class="status-indicator ${s.is_running ? 'live' : 'offline'}" style="width: 14px; height: 14px;"></div>
        </div>
        <div>
          <div style="font-family: var(--font-mono); font-size: 20px; font-weight: 700; color: ${statusColor};">${statusText}</div>
          <div style="font-size: 12px; color: var(--text-tertiary);">Mode: ${modeText} • Dry Run: ${s.dry_run ? 'ON' : 'OFF'}</div>
        </div>
      </div>
    `;
  }

  // Metrics
  const metricsEl = document.getElementById('dep-metrics');
  if (metricsEl) {
    const uptime = s.uptime_seconds || 0;
    const uptimeStr = uptime > 3600
      ? `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`
      : uptime > 60
        ? `${Math.floor(uptime / 60)}m ${Math.floor(uptime % 60)}s`
        : `${Math.floor(uptime)}s`;

    metricsEl.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${[
          ['Uptime', uptimeStr],
          ['Last Heartbeat', s.last_heartbeat ? timeAgo(s.last_heartbeat) : 'Never'],
          ['Signals Evaluated', s.signals_evaluated || 0],
          ['Trades Executed', s.trades_executed || 0],
          ['Daily P&L', `$${(s.daily_pnl || 0).toFixed(2)}`],
        ].map(([k, v]) => `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">${k}</span>
            <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600;">${v}</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  // Positions
  const posEl = document.getElementById('dep-positions');
  if (posEl) {
    const positions = s.active_positions || [];
    if (positions.length > 0) {
      posEl.innerHTML = positions.map(p => `
        <div style="padding: 10px; background: var(--bg-elevated); border-radius: var(--radius-md); margin-bottom: 8px;">
          <div style="font-weight: 600; font-size: 13px;">${p.strategy || 'Unknown'}</div>
          <div style="font-size: 11px; color: var(--text-tertiary);">Entry: $${(p.entry_price || 0).toFixed(2)} • ${p.trade_type || 'Long'}</div>
        </div>
      `).join('');
    } else {
      posEl.innerHTML = `<div style="font-size: 12px; color: var(--text-tertiary); text-align: center; padding: var(--space-md);">No active positions</div>`;
    }
  }

  // Errors
  const errEl = document.getElementById('dep-errors');
  if (errEl) {
    const errors = s.errors || [];
    if (errors.length > 0) {
      errEl.innerHTML = errors.slice(0, 5).map(e => `
        <div style="font-size: 11px; color: var(--accent-red); font-family: var(--font-mono); padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">${e}</div>
      `).join('');
    } else {
      errEl.innerHTML = `<div style="font-size: 12px; color: var(--accent-green); text-align: center; padding: var(--space-md);">No errors ✓</div>`;
    }
  }

  // Update button states
  const startPaper = document.getElementById('dep-start-paper');
  const startLive = document.getElementById('dep-start-live');
  const stopBtn = document.getElementById('dep-stop');

  if (startPaper) startPaper.disabled = s.is_running;
  if (startLive) startLive.disabled = s.is_running;
  if (stopBtn) stopBtn.disabled = !s.is_running;
}

async function startEngine(mode) {
  if (mode === 'live') {
    const confirmed = confirm(
      '⚠️ WARNING: Starting LIVE trading mode.\n\n' +
      'This will execute REAL trades with REAL money.\n' +
      'Make sure dry_run is disabled in config.\n\n' +
      'Are you absolutely sure?'
    );
    if (!confirmed) return;
  }

  try {
    const result = await api.startTrading({
      mode,
      confirm: mode === 'live',
    });

    if (result.success) {
      toast(`Engine started in ${mode} mode`, 'success');
    } else {
      toast(`Start failed: ${result.message}`, 'error');
    }
  } catch (e) {
    toast('Failed to start engine', 'error');
  }

  await refreshStatus();
}

async function stopEngine() {
  try {
    const result = await api.stopTrading();
    toast(result.success ? 'Engine stopped' : `Stop failed: ${result.message}`, result.success ? 'info' : 'error');
  } catch (e) {
    toast('Failed to stop engine', 'error');
  }
  await refreshStatus();
}

async function emergencyStop() {
  const confirmed = confirm(
    '🚨 EMERGENCY STOP\n\n' +
    'This will:\n' +
    '• Close ALL open positions immediately\n' +
    '• Halt the trading engine\n\n' +
    'This action cannot be undone. Proceed?'
  );
  if (!confirmed) return;

  try {
    const result = await api.emergencyStop();
    toast(
      result.success
        ? `Emergency stop executed. ${result.positions_closed} positions closed.`
        : `Emergency stop failed: ${result.message}`,
      result.success ? 'error' : 'error'
    );
  } catch (e) {
    toast('Emergency stop failed!', 'error');
  }
  await refreshStatus();
}

// Cleanup interval when navigating away
export function destroyDeployment() {
  if (statusInterval) {
    clearInterval(statusInterval);
    statusInterval = null;
  }
}

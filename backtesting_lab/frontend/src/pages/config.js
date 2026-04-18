/**
 * Configuration Page — System settings with live editing and persistence.
 */
import { api } from '../api.js';
import { toast } from '../utils.js';

let currentConfig = {};

export async function renderConfig(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <div>
          <div class="page-badge">⚙ SETTINGS</div>
          <h2 class="page-title">System <span>Configuration</span></h2>
          <p class="page-subtitle">Manage strategies, risk parameters, ML settings, and notifications</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-ghost btn-sm" id="cfg-reset">Reset Defaults</button>
          <button class="btn btn-primary btn-sm" id="cfg-save">Save Changes</button>
        </div>
      </div>

      <div class="grid-2" style="gap: var(--space-lg);">
        <!-- Left Column -->
        <div>
          <!-- System -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">System</span></div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Trading Mode</label>
                <select class="input cfg-field" data-path="system.mode">
                  <option value="paper">Paper Trading</option>
                  <option value="live">Live Trading</option>
                  <option value="backtest_only">Backtest Only</option>
                </select>
              </div>
              <div class="input-group">
                <label class="input-label">Dry Run</label>
                <select class="input cfg-field" data-path="system.dry_run">
                  <option value="true">Enabled (Safe)</option>
                  <option value="false">Disabled (Executes)</option>
                </select>
              </div>
            </div>
            <div class="input-group">
              <label class="input-label">Log Level</label>
              <select class="input cfg-field" data-path="system.log_level">
                <option value="DEBUG">Debug</option>
                <option value="INFO">Info</option>
                <option value="WARNING">Warning</option>
                <option value="ERROR">Error</option>
              </select>
            </div>
          </div>

          <!-- Risk Management -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Risk Management</span></div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Initial Capital ($)</label>
                <input type="number" class="input cfg-field" data-path="risk.initial_capital" step="10000" />
              </div>
              <div class="input-group">
                <label class="input-label">Risk Per Trade (%)</label>
                <input type="number" class="input cfg-field" data-path="risk.risk_per_trade_pct" step="0.1" min="0.1" max="10" />
              </div>
            </div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Max Daily Loss (%)</label>
                <input type="number" class="input cfg-field" data-path="risk.max_daily_loss_pct" step="0.5" min="0" />
              </div>
              <div class="input-group">
                <label class="input-label">Max Open Positions</label>
                <input type="number" class="input cfg-field" data-path="risk.max_open_positions" min="1" max="10" />
              </div>
            </div>
            <div class="grid-3" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Stop Loss (%)</label>
                <input type="number" class="input cfg-field" data-path="risk.global_stop_loss_pct" step="0.5" min="0" />
              </div>
              <div class="input-group">
                <label class="input-label">Take Profit (%)</label>
                <input type="number" class="input cfg-field" data-path="risk.global_take_profit_pct" step="0.5" min="0" />
              </div>
              <div class="input-group">
                <label class="input-label">Trailing Stop (%)</label>
                <input type="number" class="input cfg-field" data-path="risk.trailing_stop_pct" step="0.5" min="0" />
              </div>
            </div>
            <div class="input-group">
              <label class="input-label">Cooldown After Loss (min)</label>
              <input type="number" class="input cfg-field" data-path="risk.cooldown_after_loss_minutes" min="0" max="120" />
            </div>
          </div>

          <!-- Broker -->
          <div class="card">
            <div class="card-header"><span class="card-label">Broker (IBKR)</span></div>
            <div class="grid-3" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Host</label>
                <input type="text" class="input cfg-field" data-path="broker.host" />
              </div>
              <div class="input-group">
                <label class="input-label">Port</label>
                <input type="number" class="input cfg-field" data-path="broker.port" />
              </div>
              <div class="input-group">
                <label class="input-label">Client ID</label>
                <input type="number" class="input cfg-field" data-path="broker.client_id" />
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column -->
        <div>
          <!-- ML Config -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">AI / Machine Learning</span></div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Confidence Threshold</label>
                <input type="number" class="input cfg-field" data-path="ml.confidence_threshold" step="0.05" min="0" max="1" />
              </div>
              <div class="input-group">
                <label class="input-label">Min Trades for Training</label>
                <input type="number" class="input cfg-field" data-path="ml.min_trades_for_training" min="5" />
              </div>
            </div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Use Ensemble</label>
                <select class="input cfg-field" data-path="ml.use_ensemble">
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div class="input-group">
                <label class="input-label">Auto Retrain</label>
                <select class="input cfg-field" data-path="ml.auto_retrain">
                  <option value="false">Disabled</option>
                  <option value="true">Enabled</option>
                </select>
              </div>
            </div>
            <div style="margin-top: var(--space-md); display: flex; gap: 8px;">
              <button class="btn btn-ghost btn-sm" id="cfg-train-base">Train Base Model</button>
              <button class="btn btn-ghost btn-sm" id="cfg-train-ensemble">Train Ensemble</button>
              <button class="btn btn-ghost btn-sm" id="cfg-export-model">Export Model</button>
            </div>
          </div>

          <!-- Schedule -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Trading Schedule</span></div>
            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Market Open</label>
                <input type="text" class="input cfg-field" data-path="schedule.market_open" />
              </div>
              <div class="input-group">
                <label class="input-label">Market Close</label>
                <input type="text" class="input cfg-field" data-path="schedule.market_close" />
              </div>
            </div>
            <div class="input-group">
              <label class="input-label">Eval Interval (seconds)</label>
              <input type="number" class="input cfg-field" data-path="schedule.eval_interval_seconds" min="10" />
            </div>
          </div>

          <!-- Notifications -->
          <div class="card">
            <div class="card-header"><span class="card-label">Notifications</span></div>
            <div class="input-group">
              <label class="input-label">Notifications Enabled</label>
              <select class="input cfg-field" data-path="notifications.enabled">
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
            <div class="input-group">
              <label class="input-label">Discord Webhook URL</label>
              <input type="text" class="input cfg-field" data-path="notifications.channels.discord.webhook_url" placeholder="https://discord.com/api/webhooks/..." />
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Load current config
  try {
    currentConfig = await api.getConfig();
    populateFields(currentConfig);
  } catch (e) {
    toast('Failed to load configuration', 'error');
  }

  // Bind buttons
  document.getElementById('cfg-save')?.addEventListener('click', saveConfig);
  document.getElementById('cfg-reset')?.addEventListener('click', resetConfig);
  document.getElementById('cfg-train-base')?.addEventListener('click', () => trainModel('base'));
  document.getElementById('cfg-train-ensemble')?.addEventListener('click', () => trainModel('ensemble'));
  document.getElementById('cfg-export-model')?.addEventListener('click', exportModel);
}

function populateFields(config) {
  document.querySelectorAll('.cfg-field').forEach(el => {
    const path = el.dataset.path;
    if (!path) return;
    const value = getNestedValue(config, path);
    if (value !== undefined) {
      el.value = String(value);
    }
  });
}

function collectChanges() {
  const updates = {};
  document.querySelectorAll('.cfg-field').forEach(el => {
    const path = el.dataset.path;
    if (!path) return;

    let value = el.value;
    const original = getNestedValue(currentConfig, path);

    // Type coerce
    if (value === 'true') value = true;
    else if (value === 'false') value = false;
    else if (!isNaN(value) && value !== '') value = parseFloat(value);

    if (value !== original) {
      setNestedValue(updates, path, value);
    }
  });
  return updates;
}

async function saveConfig() {
  const updates = collectChanges();
  if (Object.keys(updates).length === 0) {
    toast('No changes to save', 'info');
    return;
  }

  try {
    const result = await api.updateConfig(updates);
    if (result.success) {
      toast('Configuration saved successfully', 'success');
      currentConfig = await api.getConfig();
    } else {
      toast(`Save failed: ${result.message}`, 'error');
    }
  } catch (e) {
    toast('Failed to save configuration', 'error');
  }
}

async function resetConfig() {
  if (!confirm('Reset all settings to defaults?')) return;
  try {
    const result = await api.resetConfig();
    if (result.success) {
      currentConfig = await api.getConfig();
      populateFields(currentConfig);
      toast('Configuration reset to defaults', 'success');
    }
  } catch (e) {
    toast('Reset failed', 'error');
  }
}

async function trainModel(mode) {
  const btn = document.getElementById(mode === 'base' ? 'cfg-train-base' : 'cfg-train-ensemble');
  if (btn) { btn.disabled = true; btn.textContent = 'Training...'; }

  try {
    const result = await api.trainModel({ mode });
    if (result.success) {
      toast(`${mode} model trained! Reliability: ${(result.reliability_score * 100).toFixed(1)}%`, 'success');
    } else {
      toast(`Training failed: ${result.message}`, 'error');
    }
  } catch (e) {
    toast('Model training failed', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = mode === 'base' ? 'Train Base Model' : 'Train Ensemble'; }
  }
}

async function exportModel() {
  try {
    const result = await api.exportModel();
    toast(result.success ? `Model exported: ${result.data?.path}` : result.message, result.success ? 'success' : 'error');
  } catch (e) {
    toast('Export failed', 'error');
  }
}

// ── Helpers ──

function getNestedValue(obj, path) {
  return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj);
}

function setNestedValue(obj, path, value) {
  const keys = path.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!current[keys[i]]) current[keys[i]] = {};
    current = current[keys[i]];
  }
  current[keys[keys.length - 1]] = value;
}

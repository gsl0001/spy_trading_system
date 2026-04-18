/**
 * Backtest Page — Strategy selection, parameter controls, and result visualization.
 */
import { api } from '../api.js';
import { formatCurrency, formatPct, formatNumber, pnlClass, toast } from '../utils.js';
import { renderMetrics } from '../components/metrics.js';
import { renderEquityChart } from '../components/chart.js';

let strategies = [];
let lastResult = null;

export async function renderBacktest(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <div>
          <div class="page-badge">⟐ LABORATORY</div>
          <h2 class="page-title">Backtest <span>Lab</span></h2>
          <p class="page-subtitle">Test strategies against historical data with full metrics</p>
        </div>
      </div>

      <div class="grid-2-1">
        <!-- Controls -->
        <div>
          <div class="card">
            <div class="card-header">
              <span class="card-label">Strategy & Parameters</span>
            </div>

            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Strategy</label>
                <select class="input" id="bt-strategy"></select>
              </div>
              <div class="input-group">
                <label class="input-label">Asset Class</label>
                <select class="input" id="bt-asset">
                  <option value="spot">Spot Equity</option>
                  <option value="options">Options (Synthetic)</option>
                </select>
              </div>
            </div>

            <div class="grid-2" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Start Date</label>
                <input type="date" class="input" id="bt-start" />
              </div>
              <div class="input-group">
                <label class="input-label">End Date</label>
                <input type="date" class="input" id="bt-end" />
              </div>
            </div>

            <div class="grid-3" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Capital ($)</label>
                <input type="number" class="input" id="bt-capital" value="100000" step="10000" />
              </div>
              <div class="input-group">
                <label class="input-label">Risk %</label>
                <input type="number" class="input" id="bt-risk" value="1.0" step="0.1" min="0.1" max="10" />
              </div>
              <div class="input-group">
                <label class="input-label">Interval</label>
                <select class="input" id="bt-interval">
                  <option value="1m">1 Minute</option>
                  <option value="5m">5 Minutes</option>
                  <option value="1d" selected>Daily</option>
                  <option value="1h">Hourly</option>
                </select>
                <div style="font-size: 9px; color: var(--text-tertiary); margin-top: 4px;">* 1m/5m limited to last 7/60 days.</div>
              </div>
            </div>

            <div class="grid-3" style="gap: var(--space-md);">
              <div class="input-group">
                <label class="input-label">Stop Loss %</label>
                <input type="number" class="input" id="bt-sl" value="0" step="0.5" min="0" />
              </div>
              <div class="input-group">
                <label class="input-label">Take Profit %</label>
                <input type="number" class="input" id="bt-tp" value="0" step="0.5" min="0" />
              </div>
              <div class="input-group">
                <label class="input-label">Trailing Stop %</label>
                <input type="number" class="input" id="bt-trail" value="0" step="0.5" min="0" />
              </div>
            </div>

            <div style="display: flex; gap: 12px; margin-top: var(--space-md);">
              <button class="btn btn-primary btn-lg" id="bt-run" style="flex: 1;">▶ Run Backtest</button>
            </div>
          </div>
        </div>

        <!-- Quick Stats -->
        <div>
          <div class="card" id="bt-quick-stats" style="margin-bottom: var(--space-md);">
            <div class="card-header"><span class="card-label">Quick Stats</span></div>
            <div class="empty-state" style="padding: var(--space-lg);"><p style="font-size: 12px;">Run a backtest to see results</p></div>
          </div>
          <div class="card" id="bt-strategy-info">
            <div class="card-header"><span class="card-label">Strategy Info</span></div>
            <div style="font-size: 12px; color: var(--text-tertiary);">Select a strategy to see details</div>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div id="bt-results" style="display: none;">
        <div class="section-label">Performance Metrics</div>
        <div class="grid-5" id="bt-metrics"></div>

        <div class="section-label">Equity Curve</div>
        <div class="card">
          <div id="bt-chart" style="min-height: 350px;"></div>
        </div>

        <div class="section-label">Trade Log</div>
        <div class="card">
          <div class="table-container" id="bt-trades"></div>
        </div>
      </div>
    </div>
  `;

  // Load strategies
  try {
    strategies = await api.strategies();
    const select = document.getElementById('bt-strategy');
    if (select) {
      strategies.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.full_name;
        opt.textContent = `${s.id}. ${s.name}`;
        select.appendChild(opt);
      });

      // Default to AI Meta-Ensemble
      const defaultStrat = strategies.find(s => s.id === 36);
      if (defaultStrat) select.value = defaultStrat.full_name;

      select.addEventListener('change', () => updateStrategyInfo(select.value));
      updateStrategyInfo(select.value);
    }
  } catch (e) {
    toast('Failed to load strategies', 'error');
  }

  // Set default dates
  const now = new Date();
  const yearAgo = new Date(now);
  yearAgo.setFullYear(now.getFullYear() - 1);
  const endEl = document.getElementById('bt-end');
  const startEl = document.getElementById('bt-start');
  if (endEl) endEl.value = now.toISOString().substring(0, 10);
  if (startEl) startEl.value = yearAgo.toISOString().substring(0, 10);

  // Run button
  document.getElementById('bt-run')?.addEventListener('click', runBacktest);
}

async function updateStrategyInfo(fullName) {
  const strat = strategies.find(s => s.full_name === fullName);
  const el = document.getElementById('bt-strategy-info');
  if (!el || !strat) return;

  // Check if this strategy is currently running
  let isLive = false;
  try {
    const status = await api.liveStatus();
    if (status.is_running && status.active_positions) {
      isLive = status.active_positions.some(p => p.strategy === fullName || p.strategy.includes(strat.name));
    }
  } catch (e) {}

  const catColors = {
    trend: 'var(--accent-blue)', breakout: 'var(--accent-green)', mean_reversion: 'var(--accent-purple)',
    momentum: 'var(--accent-orange)', volatility: 'var(--accent-yellow)', ai: 'var(--accent-blue)',
    macro: 'var(--accent-purple)', sentiment: 'var(--accent-green)', options: 'var(--accent-red)',
  };

  el.innerHTML = `
    <div class="card-header"><span class="card-label">Strategy Info</span></div>
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
      <div style="font-weight: 600; font-size: 14px;">${strat.name}</div>
      ${isLive ? '<span style="font-size: 9px; padding: 2px 6px; background: var(--accent-green); color: white; border-radius: 4px; font-weight: 800; animation: pulse 2s infinite;">LIVE ACTIVE</span>' : ''}
    </div>
    <div style="display: flex; gap: 6px; flex-wrap: wrap;">
      <span style="font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); background: ${catColors[strat.category] || 'var(--bg-elevated)'}20; color: ${catColors[strat.category] || 'var(--text-secondary)'}; border: 1px solid ${catColors[strat.category] || 'var(--border-default)'}30;">${strat.category}</span>
      <span style="font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); background: var(--bg-elevated); color: var(--text-tertiary);">ID: ${strat.id}</span>
    </div>
  `;
}

async function runBacktest() {
  const btn = document.getElementById('bt-run');
  const resultsEl = document.getElementById('bt-results');
  if (!btn) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running...';

  try {
    const params = {
      strategy: document.getElementById('bt-strategy')?.value || '',
      start_date: document.getElementById('bt-start')?.value || '',
      end_date: document.getElementById('bt-end')?.value || '',
      interval: document.getElementById('bt-interval')?.value || '1d',
      initial_capital: parseFloat(document.getElementById('bt-capital')?.value || 100000),
      risk_pct: parseFloat(document.getElementById('bt-risk')?.value || 1.0),
      asset_class: document.getElementById('bt-asset')?.value || 'spot',
      global_stop_loss: parseFloat(document.getElementById('bt-sl')?.value || 0),
      global_take_profit: parseFloat(document.getElementById('bt-tp')?.value || 0),
      trailing_stop: parseFloat(document.getElementById('bt-trail')?.value || 0),
      use_ml: true,
    };

    const result = await api.runBacktest(params);
    lastResult = result;

    if (!result.success) {
      toast(`Backtest failed: ${result.error}`, 'error');
      return;
    }

    if (resultsEl) resultsEl.style.display = 'block';

    // Metrics
    const m = result.metrics;
    const metricsEl = document.getElementById('bt-metrics');
    if (metricsEl) {
      renderMetrics(metricsEl, [
        { label: 'Total Return', value: m.total_return_pct, format: 'pct', icon: '💰' },
        { label: 'Max Drawdown', value: m.max_drawdown_pct, format: 'pct', color: 'var(--accent-red)', icon: '📉' },
        { label: 'Win Rate', value: m.win_rate_pct, format: 'pct', color: 'var(--text-primary)', icon: '🎯' },
        { label: 'Sharpe Ratio', value: m.sharpe_ratio, format: 'ratio', color: 'var(--accent-blue)', icon: '📊' },
        { label: 'Profit Factor', value: m.profit_factor, format: 'ratio', color: 'var(--accent-green)', icon: '⚡' },
      ]);
    }

    // Quick stats
    const quickEl = document.getElementById('bt-quick-stats');
    if (quickEl) {
      quickEl.innerHTML = `
        <div class="card-header"><span class="card-label">Quick Stats</span></div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${[
            ['Trades', m.trade_count],
            ['Avg Win', formatPct(m.avg_win)],
            ['Avg Loss', formatPct(m.avg_loss)],
            ['Payoff', formatNumber(m.payoff_ratio, 2) + 'x'],
            ['Sortino', formatNumber(m.sortino_ratio, 2)],
            ['Recovery', formatNumber(m.recovery_factor, 2)],
            ['Collisions', result.collisions || 0],
          ].map(([k, v]) => `
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 12px; color: var(--text-secondary);">${k}</span>
              <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600;">${v}</span>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Equity chart
    const chartEl = document.getElementById('bt-chart');
    if (chartEl && result.equity_curve.length > 0) {
      const lastVal = result.equity_curve[result.equity_curve.length - 1]?.value || 0;
      const firstVal = result.equity_curve[0]?.value || 0;
      const color = lastVal >= firstVal ? '#30D158' : '#FF453A';
      renderEquityChart(chartEl, result.equity_curve, { color, height: 340 });
    }

    // Trade log
    const tradesEl = document.getElementById('bt-trades');
    if (tradesEl && result.trades.length > 0) {
      tradesEl.innerHTML = `
        <table>
          <thead>
            <tr><th>#</th><th>Entry Date</th><th>Exit Date</th><th>Type</th><th>Entry</th><th>Exit</th><th>P&L</th><th>P&L %</th></tr>
          </thead>
          <tbody>
            ${result.trades.map((t, i) => `
              <tr>
                <td>${i + 1}</td>
                <td>${String(t.date_in).substring(0, 10)}</td>
                <td>${String(t.date_out).substring(0, 10)}</td>
                <td>${t.trade_type}</td>
                <td>${formatCurrency(t.entry_price)}</td>
                <td>${formatCurrency(t.exit_price)}</td>
                <td class="${pnlClass(t.pnl)}">${formatCurrency(t.pnl)}</td>
                <td class="${pnlClass(t.pnl_pct)}">${formatPct(t.pnl_pct)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    toast(`Backtest complete: ${m.trade_count} trades, ${formatPct(m.total_return_pct)} return`, 'success');

  } catch (err) {
    console.error('Backtest error:', err);
    toast('Backtest failed. Check server logs.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Run Backtest';
  }
}

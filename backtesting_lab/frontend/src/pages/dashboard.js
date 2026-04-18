/**
 * Dashboard Page — Main trading overview with KPIs, price, and signals.
 */
import { api } from '../api.js';
import { formatCurrency, formatPct, formatNumber, formatVolume, pnlClass, toast } from '../utils.js';
import { renderMetrics, renderHeroMetric } from '../components/metrics.js';
import { renderEquityChart } from '../components/chart.js';

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <div>
          <div class="page-badge">◈ LIVE MONITOR</div>
          <h2 class="page-title">Trading <span>Dashboard</span></h2>
          <p class="page-subtitle">Real-time market overview and system diagnostics</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-ghost btn-sm" id="dash-refresh">↻ Refresh</button>
        </div>
      </div>

      <!-- Price Hero -->
      <div class="card" style="margin-bottom: var(--space-md);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
              <span style="font-size: 13px; font-weight: 700; color: var(--text-secondary);">SPY</span>
              <span style="font-size: 10px; color: var(--text-tertiary); background: var(--bg-elevated); padding: 2px 8px; border-radius: var(--radius-full);">SPDR S&P 500 ETF</span>
            </div>
            <div id="dash-hero-price"></div>
          </div>
          <div id="dash-market-info" style="text-align: right; font-size: 12px; color: var(--text-tertiary);"></div>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="grid-4" id="dash-kpis"></div>

      <!-- Charts Row -->
      <div class="section-label">System Performance</div>
      <div class="grid-2-1">
        <div class="card">
          <div class="card-header">
            <span class="card-label">Portfolio Equity Curve</span>
          </div>
          <div id="dash-equity-chart" style="min-height: 320px;"></div>
        </div>
        <div>
          <!-- ML Status -->
          <div class="card" style="margin-bottom: var(--space-md);">
            <div class="card-header">
              <span class="card-label">AI Engine Status</span>
            </div>
            <div id="dash-ml-status"></div>
          </div>
          <!-- System Health -->
          <div class="card">
            <div class="card-header">
              <span class="card-label">System Health</span>
            </div>
            <div id="dash-system-health"></div>
          </div>
        </div>
      </div>

      <!-- Recent Trades -->
      <div class="section-label">Recent Trades</div>
      <div class="card">
        <div class="table-container" id="dash-trades-table"></div>
      </div>
    </div>
  `;

  // Bind refresh
  document.getElementById('dash-refresh')?.addEventListener('click', () => loadDashboardData());

  // Load data
  await loadDashboardData();
}

async function loadDashboardData() {
  try {
    // Fetch all data in parallel
    const [marketData, health, mlStatus, tradesRes, perfReport] = await Promise.allSettled([
      api.marketData(),
      api.health(),
      api.mlStatus(),
      api.trades({ limit: 10 }),
      api.performanceReport('30d'),
    ]);

    const market = marketData.status === 'fulfilled' ? marketData.value : {};
    const sys = health.status === 'fulfilled' ? health.value : {};
    const ml = mlStatus.status === 'fulfilled' ? mlStatus.value : {};
    const trades = tradesRes.status === 'fulfilled' ? tradesRes.value : { trades: [] };
    const perf = perfReport.status === 'fulfilled' ? perfReport.value : {};

    // Price hero
    const heroEl = document.getElementById('dash-hero-price');
    if (heroEl && market.price) {
      renderHeroMetric(heroEl, {
        label: `Last Update: ${market.timestamp || 'N/A'}`,
        value: market.price,
        format: 'currency',
        change: market.change_pct,
        changeLabel: `(${formatCurrency(market.change)})`,
      });
    }

    // Market info
    const infoEl = document.getElementById('dash-market-info');
    if (infoEl && market.price) {
      infoEl.innerHTML = `
        <div style="margin-bottom: 4px;"><span style="color: var(--text-secondary);">O</span> ${formatCurrency(market.open)} <span style="color: var(--text-secondary); margin-left: 8px;">H</span> ${formatCurrency(market.high)}</div>
        <div style="margin-bottom: 4px;"><span style="color: var(--text-secondary);">L</span> ${formatCurrency(market.low)} <span style="color: var(--text-secondary); margin-left: 8px;">Vol</span> ${formatVolume(market.volume)}</div>
        <div><span style="color: var(--text-secondary);">RSI</span> ${formatNumber(market.rsi, 1)} <span style="color: var(--text-secondary); margin-left: 8px;">VIX</span> ${formatNumber(market.vix, 1)}</div>
      `;
    }

    // KPIs
    const kpiEl = document.getElementById('dash-kpis');
    if (kpiEl) {
      const confidence = (ml.confidence_threshold || 0.75) * 100;
      const confColor = confidence >= 80 ? 'var(--accent-green)' : (confidence >= 60 ? 'var(--accent-yellow)' : 'var(--accent-red)');

      renderMetrics(kpiEl, [
        { label: 'Net P&L', value: perf.total_pnl || 0, format: 'pnl', icon: '💰' },
        { label: 'Win Rate', value: perf.win_rate || 0, format: 'pct', color: 'var(--text-primary)', icon: '🎯' },
        { label: 'Profit Factor', value: perf.profit_factor || 0, format: 'ratio', color: 'var(--accent-blue)', icon: '📈' },
        { 
          label: 'AI Confidence', 
          value: confidence, 
          format: 'pct', 
          color: confColor, 
          icon: '🤖',
          sublabel: `<div style="height: 4px; width: 100%; background: var(--bg-elevated); border-radius: 2px; margin-top: 8px; overflow: hidden;">
                       <div style="height: 100%; width: ${confidence}%; background: ${confColor}; transition: width 0.5s ease-out;"></div>
                     </div>`
        },
      ]);
    }

    // Equity chart
    const chartEl = document.getElementById('dash-equity-chart');
    if (chartEl && perf.equity_curve && perf.equity_curve.length > 0) {
      const lastVal = perf.equity_curve[perf.equity_curve.length - 1]?.value || 0;
      const color = lastVal >= 0 ? '#30D158' : '#FF453A';
      renderEquityChart(chartEl, perf.equity_curve, { color, height: 300 });
    } else if (chartEl) {
      chartEl.innerHTML = `<div class="empty-state" style="height: 300px; display: flex; align-items: center; justify-content: center;"><div><div class="empty-state-icon">📈</div><h3>No Performance Data</h3><p>Run a backtest or start trading to see equity curve</p></div></div>`;
    }

    // ML Status
    const mlEl = document.getElementById('dash-ml-status');
    if (mlEl) {
      const confidence = (ml.confidence_threshold || 0.75) * 100;
      const confColor = confidence >= 80 ? 'var(--accent-green)' : (confidence >= 60 ? 'var(--accent-yellow)' : 'var(--accent-red)');

      mlEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Base Model</span>
            <span style="font-size: 12px; font-weight: 600; color: ${ml.is_trained ? 'var(--accent-green)' : 'var(--accent-red)'};">
              ${ml.is_trained ? '● Trained' : '○ Untrained'}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Ensemble</span>
            <span style="font-size: 12px; font-weight: 600; color: ${ml.is_ensemble_trained ? 'var(--accent-green)' : 'var(--accent-red)'};">
              ${ml.is_ensemble_trained ? '● Active' : '○ Inactive'}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Features</span>
            <span style="font-family: var(--font-mono); font-size: 13px;">${ml.feature_count || 0}</span>
          </div>
          
          <div style="margin-top: 4px; padding-top: 8px; border-top: 1px solid var(--bg-elevated);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 12px; color: var(--text-secondary);">Confidence Meter</span>
              <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: ${confColor};">
                ${formatPct(confidence)}
              </span>
            </div>
            <div style="height: 8px; width: 100%; background: var(--bg-elevated); border-radius: 4px; overflow: hidden;">
              <div style="height: 100%; width: ${confidence}%; background: ${confColor}; transition: width 0.5s ease-out;"></div>
            </div>
          </div>
        </div>
      `;
    }

    // System Health
    const healthEl = document.getElementById('dash-system-health');
    if (healthEl) {
      healthEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Server</span>
            <span style="font-size: 12px; font-weight: 600; color: ${sys.status === 'ok' ? 'var(--accent-green)' : 'var(--accent-red)'};">
              ${sys.status === 'ok' ? '● Online' : '○ Offline'}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Mode</span>
            <span style="font-size: 12px; font-weight: 600; color: var(--accent-yellow);">
              ${sys.mode || 'paper'}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Dry Run</span>
            <span style="font-size: 12px; font-weight: 600; color: ${sys.dry_run ? 'var(--accent-yellow)' : 'var(--accent-green)'};">
              ${sys.dry_run ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: var(--text-secondary);">Journal</span>
            <span style="font-family: var(--font-mono); font-size: 13px;">${sys.journal_trades || 0} trades</span>
          </div>
        </div>
      `;
    }

    // Recent Trades Table
    const tableEl = document.getElementById('dash-trades-table');
    if (tableEl) {
      if (trades.trades && trades.trades.length > 0) {
        tableEl.innerHTML = `
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Strategy</th>
                <th>Type</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>P&L</th>
                <th>P&L %</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              ${trades.trades.slice(0, 10).map(t => `
                <tr>
                  <td>${String(t.date_out || '').substring(0, 10)}</td>
                  <td style="color: var(--text-primary); font-family: var(--font-sans); font-weight: 500;">${t.strategy || '—'}</td>
                  <td>${t.trade_type || 'Long'}</td>
                  <td>${formatCurrency(t.entry_price)}</td>
                  <td>${formatCurrency(t.exit_price)}</td>
                  <td class="${pnlClass(t.pnl)}">${formatCurrency(t.pnl)}</td>
                  <td class="${pnlClass(t.pnl_pct)}">${formatPct(t.pnl_pct)}</td>
                  <td><span style="font-size: 10px; background: var(--bg-elevated); padding: 2px 6px; border-radius: var(--radius-sm);">${t.source || 'backtest'}</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      } else {
        tableEl.innerHTML = `<div class="empty-state"><h3>No Trades Yet</h3><p>Run a backtest or start auto-trading to see trade history.</p></div>`;
      }
    }

  } catch (err) {
    console.error('Dashboard load failed:', err);
    toast('Failed to load dashboard data. Is the server running?', 'error');
  }
}

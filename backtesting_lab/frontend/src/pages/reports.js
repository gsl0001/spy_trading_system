/**
 * Reports Page — Performance analytics, trade history, and exports.
 */
import { api } from '../api.js';
import { formatCurrency, formatPct, formatNumber, pnlClass, toast } from '../utils.js';
import { renderMetrics } from '../components/metrics.js';
import { renderEquityChart, renderPnLBars } from '../components/chart.js';

export async function renderReports(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <div>
          <div class="page-badge">◩ ANALYTICS</div>
          <h2 class="page-title">Performance <span>Reports</span></h2>
          <p class="page-subtitle">Historical analytics, strategy attribution, and trade exports</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <select class="input" id="rpt-period" style="width: 140px;">
            <option value="7d">7 Days</option>
            <option value="30d" selected>30 Days</option>
            <option value="90d">90 Days</option>
            <option value="1y">1 Year</option>
            <option value="3y">3 Years</option>
          </select>
          <button class="btn btn-ghost btn-sm" id="rpt-refresh">↻ Load</button>
          <button class="btn btn-ghost btn-sm" id="rpt-csv">⇩ CSV</button>
        </div>
      </div>

      <!-- KPI Row -->
      <div class="grid-5" id="rpt-kpis"></div>

      <!-- Charts -->
      <div class="section-label">Equity & P&L</div>
      <div class="grid-1-1">
        <div class="card">
          <div class="card-header"><span class="card-label">Cumulative Equity</span></div>
          <div id="rpt-equity" style="min-height: 280px;"></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-label">Daily P&L</span></div>
          <div id="rpt-pnl-bars" style="min-height: 280px;"></div>
        </div>
      </div>

      <!-- Strategy Breakdown -->
      <div class="section-label">Strategy Attribution</div>
      <div class="card">
        <div class="table-container" id="rpt-strategy-table"></div>
      </div>

      <!-- Trade History -->
      <div class="section-label">Trade History</div>
      <div class="card">
        <div class="table-container" id="rpt-trades-table"></div>
      </div>
    </div>
  `;

  // Bind events
  document.getElementById('rpt-refresh')?.addEventListener('click', loadReportData);
  document.getElementById('rpt-period')?.addEventListener('change', loadReportData);
  document.getElementById('rpt-csv')?.addEventListener('click', exportCSV);

  // Initial load
  await loadReportData();
}

async function loadReportData() {
  const period = document.getElementById('rpt-period')?.value || '30d';

  try {
    const [perf, stratPerf, tradesRes] = await Promise.allSettled([
      api.performanceReport(period),
      api.strategyPerformance(),
      api.trades({ limit: 100 }),
    ]);

    const report = perf.status === 'fulfilled' ? perf.value : {};
    const strategies = stratPerf.status === 'fulfilled' ? stratPerf.value.strategies || [] : [];
    const trades = tradesRes.status === 'fulfilled' ? tradesRes.value.trades || [] : [];

    // KPIs
    const kpiEl = document.getElementById('rpt-kpis');
    if (kpiEl) {
      renderMetrics(kpiEl, [
        { label: 'Total P&L', value: report.total_pnl || 0, format: 'pnl', icon: '💰' },
        { label: 'Win Rate', value: report.win_rate || 0, format: 'pct', color: 'var(--text-primary)', icon: '🎯' },
        { label: 'Sharpe', value: report.sharpe || 0, format: 'ratio', color: 'var(--accent-blue)', icon: '📊' },
        { label: 'Best Day', value: report.best_day || 0, format: 'pnl', icon: '🟢' },
        { label: 'Worst Day', value: report.worst_day || 0, format: 'pnl', icon: '🔴' },
      ]);
    }

    // Equity chart
    const eqEl = document.getElementById('rpt-equity');
    if (eqEl && report.equity_curve && report.equity_curve.length > 0) {
      const lastVal = report.equity_curve[report.equity_curve.length - 1]?.value || 0;
      renderEquityChart(eqEl, report.equity_curve, {
        color: lastVal >= 0 ? '#30D158' : '#FF453A',
        height: 260,
      });
    } else if (eqEl) {
      eqEl.innerHTML = `<div class="empty-state" style="height: 260px;"><h3>No Data</h3></div>`;
    }

    // P&L bars
    const pnlEl = document.getElementById('rpt-pnl-bars');
    if (pnlEl && report.daily_returns && report.daily_returns.length > 0) {
      renderPnLBars(pnlEl, report.daily_returns, { height: 260 });
    } else if (pnlEl) {
      pnlEl.innerHTML = `<div class="empty-state" style="height: 260px;"><h3>No P&L Data</h3></div>`;
    }

    // Strategy table
    const stratEl = document.getElementById('rpt-strategy-table');
    if (stratEl && strategies.length > 0) {
      stratEl.innerHTML = `
        <table>
          <thead>
            <tr><th>Strategy</th><th>Trades</th><th>Wins</th><th>Win Rate</th><th>Total P&L</th><th>Avg P&L</th></tr>
          </thead>
          <tbody>
            ${strategies.map(s => `
              <tr>
                <td style="color: var(--text-primary); font-family: var(--font-sans); font-weight: 500;">${s.strategy}</td>
                <td>${s.trades}</td>
                <td>${s.wins}</td>
                <td>${formatPct(s.win_rate)}</td>
                <td class="${pnlClass(s.total_pnl)}">${formatCurrency(s.total_pnl)}</td>
                <td class="${pnlClass(s.avg_pnl)}">${formatCurrency(s.avg_pnl)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else if (stratEl) {
      stratEl.innerHTML = `<div class="empty-state"><h3>No Strategy Data</h3><p>Complete some trades to see strategy attribution.</p></div>`;
    }

    // Trade history
    const tradeEl = document.getElementById('rpt-trades-table');
    if (tradeEl && trades.length > 0) {
      tradeEl.innerHTML = `
        <table>
          <thead>
            <tr><th>#</th><th>Date</th><th>Strategy</th><th>Type</th><th>Entry</th><th>Exit</th><th>P&L</th><th>P&L %</th><th>Source</th></tr>
          </thead>
          <tbody>
            ${trades.map((t, i) => `
              <tr>
                <td>${t.id || i + 1}</td>
                <td>${String(t.date_out || '').substring(0, 10)}</td>
                <td style="color: var(--text-primary); font-family: var(--font-sans);">${t.strategy || '—'}</td>
                <td>${t.trade_type}</td>
                <td>${formatCurrency(t.entry_price)}</td>
                <td>${formatCurrency(t.exit_price)}</td>
                <td class="${pnlClass(t.pnl)}">${formatCurrency(t.pnl)}</td>
                <td class="${pnlClass(t.pnl_pct)}">${formatPct(t.pnl_pct)}</td>
                <td><span style="font-size: 10px; background: var(--bg-elevated); padding: 2px 6px; border-radius: var(--radius-sm);">${t.source}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else if (tradeEl) {
      tradeEl.innerHTML = `<div class="empty-state"><h3>No Trades</h3><p>Run backtests or start trading to populate trade history.</p></div>`;
    }

  } catch (err) {
    console.error('Report load failed:', err);
    toast('Failed to load report data', 'error');
  }
}

async function exportCSV() {
  try {
    const csv = await api.exportCSV();
    // Trigger download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quantos_trades_${new Date().toISOString().substring(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast('CSV exported successfully', 'success');
  } catch (e) {
    toast('CSV export failed', 'error');
  }
}

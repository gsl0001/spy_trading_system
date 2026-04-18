/**
 * Metric Cards Component — KPI display with animated values and delta indicators.
 */
import { formatCurrency, formatPct, formatNumber, pnlBgClass, pnlClass } from '../utils.js';

/**
 * Render a grid of metric cards.
 * @param {HTMLElement} container
 * @param {Array} metrics - [{label, value, format, delta, icon}]
 */
export function renderMetrics(container, metrics) {
  container.innerHTML = metrics.map(m => {
    const formatted = formatMetricValue(m.value, m.format);
    const deltaHtml = m.delta != null ? `<div class="metric-delta ${pnlBgClass(m.delta)}">${m.delta >= 0 ? '↑' : '↓'} ${formatPct(Math.abs(m.delta))}</div>` : '';
    const colorStyle = m.color ? `color: ${m.color}` : (m.format === 'pnl' ? `color: ${parseFloat(m.value) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}` : '');

    return `
      <div class="card" id="metric-${m.id || m.label.toLowerCase().replace(/\s+/g, '-')}">
        <div class="card-header">
          <span class="card-label">${m.label}</span>
          ${m.icon ? `<div class="card-icon"><span style="font-size: 14px">${m.icon}</span></div>` : ''}
        </div>
        <div class="metric-value" style="${colorStyle}">${formatted}</div>
        ${deltaHtml}
        ${m.sublabel ? `<div style="font-size: 11px; color: var(--text-tertiary); margin-top: 6px;">${m.sublabel}</div>` : ''}
      </div>
    `;
  }).join('');
}

function formatMetricValue(value, format) {
  switch (format) {
    case 'currency': return formatCurrency(value);
    case 'pnl': return formatCurrency(value);
    case 'pct': return formatPct(value);
    case 'number': return formatNumber(value, 0);
    case 'ratio': return formatNumber(value, 2);
    case 'decimal': return formatNumber(value, 2);
    default: return String(value);
  }
}

/**
 * Render a single large hero metric.
 */
export function renderHeroMetric(container, { label, value, format, change, changeLabel }) {
  const formatted = formatMetricValue(value, format);
  const changeFormatted = change != null ? formatMetricValue(change, format === 'currency' ? 'currency' : 'pct') : '';

  container.innerHTML = `
    <div style="display: flex; align-items: baseline; gap: 16px;">
      <div class="metric-value" style="font-size: 42px;">${formatted}</div>
      ${change != null ? `
        <div class="metric-delta ${pnlBgClass(change)}" style="font-size: 14px; padding: 4px 12px;">
          ${change >= 0 ? '↑' : '↓'} ${changeFormatted}
          ${changeLabel ? `<span style="color: var(--text-tertiary); margin-left: 4px;">${changeLabel}</span>` : ''}
        </div>
      ` : ''}
    </div>
    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">${label}</div>
  `;
}

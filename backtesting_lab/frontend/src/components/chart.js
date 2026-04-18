/**
 * Chart Component — Reusable wrapper for equity curves and P&L charts.
 * Uses canvas-based rendering for performance.
 */

/**
 * Render an equity curve chart using Canvas 2D.
 * @param {HTMLElement} container - Container element
 * @param {Array} data - [{time, value}]
 * @param {Object} options - {color, height, showGrid, showLabels, fill}
 */
export function renderEquityChart(container, data, options = {}) {
  const {
    color = '#0A84FF',
    height = 320,
    showGrid = true,
    showLabels = true,
    fill = true,
    lineWidth = 2,
  } = options;

  if (!data || data.length < 2) {
    container.innerHTML = `<div class="empty-state" style="height: ${height}px; display: flex; align-items: center; justify-content: center;"><div><div class="empty-state-icon">📈</div><h3>No Data</h3><p>Run a backtest to see equity curve</p></div></div>`;
    return;
  }

  const dpr = window.devicePixelRatio || 1;
  const width = container.clientWidth || 800;
  
  container.innerHTML = '';
  const canvas = document.createElement('canvas');
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  container.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const padding = { top: 20, right: 20, bottom: showLabels ? 40 : 10, left: showLabels ? 70 : 10 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = data.map(d => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  const toX = (i) => padding.left + (i / (data.length - 1)) * chartW;
  const toY = (v) => padding.top + (1 - (v - minVal) / range) * chartH;

  // Grid lines
  if (showGrid) {
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (i / gridLines) * chartH;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
    }
  }

  // Y-axis labels
  if (showLabels) {
    ctx.fillStyle = '#71717A';
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const val = maxVal - (i / gridLines) * range;
      const y = padding.top + (i / gridLines) * chartH;
      ctx.fillText(`$${val.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, padding.left - 8, y + 4);
    }

    // X-axis labels (sparse)
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(data.length / 6));
    for (let i = 0; i < data.length; i += step) {
      const label = data[i].time;
      const shortLabel = label.length > 10 ? label.substring(5, 10) : label;
      ctx.fillText(shortLabel, toX(i), height - padding.bottom + 20);
    }
  }

  // Zero line
  const startVal = values[0];
  if (startVal >= minVal && startVal <= maxVal) {
    const zeroY = toY(startVal);
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding.left, zeroY);
    ctx.lineTo(width - padding.right, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Fill area
  if (fill) {
    const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    const rgb = color === '#30D158' ? '48,209,88' : color === '#FF453A' ? '255,69,58' : '10,132,255';
    gradient.addColorStop(0, `rgba(${rgb}, 0.15)`);
    gradient.addColorStop(1, `rgba(${rgb}, 0.01)`);
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.moveTo(toX(0), height - padding.bottom);
    for (let i = 0; i < data.length; i++) {
      ctx.lineTo(toX(i), toY(values[i]));
    }
    ctx.lineTo(toX(data.length - 1), height - padding.bottom);
    ctx.closePath();
    ctx.fill();
  }

  // Main line
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(values[0]));
  for (let i = 1; i < data.length; i++) {
    ctx.lineTo(toX(i), toY(values[i]));
  }
  ctx.stroke();

  // End dot
  const lastX = toX(data.length - 1);
  const lastY = toY(values[values.length - 1]);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(0,0,0,0.3)';
  ctx.lineWidth = 1;
  ctx.stroke();
}

/**
 * Render a bar chart for daily P&L.
 */
export function renderPnLBars(container, data, options = {}) {
  const { height = 250 } = options;

  if (!data || data.length === 0) {
    container.innerHTML = `<div class="empty-state" style="height: ${height}px; display: flex; align-items: center; justify-content: center;"><div><h3>No P&L Data</h3></div></div>`;
    return;
  }

  const dpr = window.devicePixelRatio || 1;
  const width = container.clientWidth || 800;

  container.innerHTML = '';
  const canvas = document.createElement('canvas');
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  container.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const padding = { top: 15, right: 15, bottom: 30, left: 60 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = data.map(d => d.pnl);
  const maxAbs = Math.max(Math.abs(Math.min(...values)), Math.abs(Math.max(...values))) || 1;

  const barWidth = Math.max(2, Math.min(20, (chartW / data.length) * 0.7));
  const gap = (chartW - barWidth * data.length) / (data.length + 1);

  const zeroY = padding.top + chartH / 2;

  // Zero line
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, zeroY);
  ctx.lineTo(width - padding.right, zeroY);
  ctx.stroke();

  // Bars
  for (let i = 0; i < data.length; i++) {
    const val = values[i];
    const x = padding.left + gap + i * (barWidth + gap);
    const barH = (Math.abs(val) / maxAbs) * (chartH / 2);
    const y = val >= 0 ? zeroY - barH : zeroY;

    ctx.fillStyle = val >= 0 ? 'rgba(48, 209, 88, 0.8)' : 'rgba(255, 69, 58, 0.8)';
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barH, 2);
    ctx.fill();
  }

  // Y-axis labels
  ctx.fillStyle = '#71717A';
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.textAlign = 'right';
  ctx.fillText(`+$${maxAbs.toFixed(0)}`, padding.left - 6, padding.top + 10);
  ctx.fillText('$0', padding.left - 6, zeroY + 4);
  ctx.fillText(`-$${maxAbs.toFixed(0)}`, padding.left - 6, height - padding.bottom - 2);
}

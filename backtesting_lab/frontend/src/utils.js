/**
 * Utility functions for the QuantOS frontend.
 */

// ── Number Formatting ──

export function formatCurrency(value, decimals = 2) {
  if (value == null || isNaN(value)) return '$0.00';
  const num = parseFloat(value);
  const sign = num >= 0 ? '' : '-';
  return `${sign}$${Math.abs(num).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

export function formatPct(value, decimals = 1) {
  if (value == null || isNaN(value)) return '0.0%';
  const num = parseFloat(value);
  return `${num >= 0 ? '+' : ''}${num.toFixed(decimals)}%`;
}

export function formatNumber(value, decimals = 2) {
  if (value == null || isNaN(value)) return '0';
  return parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function formatVolume(value) {
  if (value == null || isNaN(value)) return '0';
  const num = Math.abs(parseFloat(value));
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return Math.round(num).toLocaleString();
}

// ── Date & Time ──

export function formatDate(date) {
  if (!date) return '';
  return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatTime(date) {
  if (!date) return '';
  return new Date(date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function formatDateTime(date) {
  if (!date) return '';
  return `${formatDate(date)} ${formatTime(date)}`;
}

export function timeAgo(dateStr) {
  if (!dateStr) return 'Never';
  const seconds = Math.floor((new Date() - new Date(dateStr)) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// ── Color Helpers ──

export function pnlColor(value) {
  if (value == null) return 'var(--text-secondary)';
  return parseFloat(value) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
}

export function pnlClass(value) {
  return parseFloat(value) >= 0 ? 'pnl-positive' : 'pnl-negative';
}

export function pnlBgClass(value) {
  return parseFloat(value) >= 0 ? 'positive' : 'negative';
}

// ── DOM Helpers ──

export function $(selector, parent = document) {
  return parent.querySelector(selector);
}

export function $$(selector, parent = document) {
  return [...parent.querySelectorAll(selector)];
}

export function createElement(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => {
    if (key === 'className') el.className = val;
    else if (key === 'innerHTML') el.innerHTML = val;
    else if (key === 'textContent') el.textContent = val;
    else if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), val);
    else if (key === 'style' && typeof val === 'object') Object.assign(el.style, val);
    else el.setAttribute(key, val);
  });
  children.forEach(child => {
    if (typeof child === 'string') el.appendChild(document.createTextNode(child));
    else if (child) el.appendChild(child);
  });
  return el;
}

// ── Toast System ──

let toastContainer = null;

function ensureToastContainer() {
  if (!toastContainer) {
    toastContainer = createElement('div', { className: 'toast-container' });
    document.body.appendChild(toastContainer);
  }
}

export function toast(message, type = 'info', duration = 4000) {
  ensureToastContainer();
  const icons = { success: '✓', error: '✗', info: 'ℹ' };
  const el = createElement('div', { className: `toast ${type}`, innerHTML: `<span style="font-size:16px">${icons[type] || 'ℹ'}</span><span>${message}</span>` });
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(100%)';
    el.style.transition = 'all 0.3s ease-in';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ── Debounce ──

export function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

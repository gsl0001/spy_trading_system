/**
 * API Client — Centralized REST + WebSocket client for QuantOS backend.
 */

const API_BASE = '';
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

// ── REST Client ──

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorBody}`);
    }

    // Handle CSV / plain text responses
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/csv') || contentType.includes('text/plain')) {
      return await response.text();
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// ── API Methods ──

export const api = {
  // Health
  health: () => request('/api/health'),
  deploymentCheck: () => request('/api/deployment/check'),
  marketData: () => request('/api/market-data/latest'),
  sparkline: () => request('/api/market-data/sparkline'),

  // Backtest
  strategies: () => request('/api/backtest/strategies'),
  runBacktest: (params) => request('/api/backtest/run', { method: 'POST', body: params }),

  // Config
  getConfig: () => request('/api/config'),
  updateConfig: (updates) => request('/api/config', { method: 'PUT', body: { updates } }),
  resetConfig: () => request('/api/config/reset', { method: 'POST' }),
  configHistory: () => request('/api/config/history'),

  // ML
  mlStatus: () => request('/api/ml/status'),
  trainModel: (params = {}) => request('/api/ml/train', { method: 'POST', body: params }),
  featureImportance: () => request('/api/ml/importance'),
  exportModel: () => request('/api/ml/export', { method: 'POST' }),

  // Live Trading
  startTrading: (params) => request('/api/live/start', { method: 'POST', body: params }),
  stopTrading: () => request('/api/live/stop', { method: 'POST' }),
  liveStatus: () => request('/api/live/status'),
  account: () => request('/api/live/account'),
  positions: () => request('/api/live/positions'),
  orders: () => request('/api/live/orders'),
  emergencyStop: () => request('/api/live/emergency-stop', { method: 'POST' }),

  // Reports
  dailyReport: (date) => request(`/api/reports/daily${date ? `?date=${date}` : ''}`),
  performanceReport: (period = '30d') => request(`/api/reports/performance?period=${period}`),
  trades: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/reports/trades${qs ? `?${qs}` : ''}`);
  },
  strategyPerformance: () => request('/api/reports/strategies'),
  exportCSV: (start, end) => {
    const params = new URLSearchParams();
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    return request(`/api/reports/export/csv${params.toString() ? `?${params}` : ''}`);
  },
};


// ── WebSocket Manager ──

class WSManager {
  constructor() {
    this._ws = null;
    this._listeners = {};
    this._reconnectTimer = null;
    this._reconnectDelay = 2000;
    this._maxReconnectDelay = 30000;
    this._connected = false;
  }

  connect() {
    try {
      this._ws = new WebSocket(WS_URL);

      this._ws.onopen = () => {
        console.log('[WS] Connected');
        this._connected = true;
        this._reconnectDelay = 2000;
        this._emit('connection', { status: 'connected' });
      };

      this._ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this._emit(msg.type, msg.data);
          this._emit('message', msg);
        } catch (e) {
          console.warn('[WS] Parse error:', e);
        }
      };

      this._ws.onclose = () => {
        console.log('[WS] Disconnected');
        this._connected = false;
        this._emit('connection', { status: 'disconnected' });
        this._scheduleReconnect();
      };

      this._ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        this._emit('error', { error });
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this._scheduleReconnect();
    }
  }

  disconnect() {
    clearTimeout(this._reconnectTimer);
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
    this._connected = false;
  }

  send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
    return () => {
      this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
    };
  }

  get isConnected() { return this._connected; }

  _emit(event, data) {
    (this._listeners[event] || []).forEach(cb => {
      try { cb(data); } catch (e) { console.error(`[WS] Listener error for '${event}':`, e); }
    });
  }

  _scheduleReconnect() {
    clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      console.log(`[WS] Reconnecting in ${this._reconnectDelay}ms...`);
      this.connect();
      this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, this._maxReconnectDelay);
    }, this._reconnectDelay);
  }
}

export const ws = new WSManager();

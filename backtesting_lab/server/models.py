"""
Pydantic models for API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# ──────────────────────────────────────────────
# Backtest
# ──────────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy: str = "Strategy 36: AI Meta-Ensemble"
    start_date: str = ""
    end_date: str = ""
    interval: str = "1d"
    initial_capital: float = 100000
    risk_pct: float = 1.0
    use_ml: bool = True
    global_stop_loss: float = 0.0
    global_take_profit: float = 0.0
    trailing_stop: float = 0.0
    max_hold_bars: int = 0
    asset_class: str = "spot"
    target_dte: int = 30
    target_delta: float = 0.50

class TradeRecord(BaseModel):
    strategy: str = ""
    date_in: str
    date_out: str
    trade_type: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    duration: Optional[int] = None

class BacktestMetrics(BaseModel):
    total_return_pct: float = 0
    max_drawdown_pct: float = 0
    win_rate_pct: float = 0
    profit_factor: float = 0
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    trade_count: int = 0
    expectancy: float = 0
    recovery_factor: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    payoff_ratio: float = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

class BacktestResponse(BaseModel):
    success: bool
    strategy: str
    metrics: BacktestMetrics
    trades: list[TradeRecord]
    equity_curve: list[dict]  # [{time, value}]
    chart_data: Optional[dict] = None
    collisions: int = 0
    error: Optional[str] = None


# ──────────────────────────────────────────────
# ML
# ──────────────────────────────────────────────

class MLTrainRequest(BaseModel):
    mode: str = "ensemble"  # "base" | "ensemble"
    strategy: Optional[str] = None

class MLStatusResponse(BaseModel):
    is_trained: bool = False
    is_ensemble_trained: bool = False
    reliability_score: float = 0.0
    confidence_threshold: float = 0.55
    feature_count: int = 0
    features: list[str] = []
    trust_scores: dict = {}

class MLTrainResponse(BaseModel):
    success: bool
    message: str
    reliability_score: float = 0.0

class FeatureImportanceResponse(BaseModel):
    features: dict  # {feature_name: importance_value}
    is_ensemble: bool = False


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    updates: dict

class ConfigHistoryItem(BaseModel):
    timestamp: str
    filename: str
    size_bytes: int


# ──────────────────────────────────────────────
# Live Trading
# ──────────────────────────────────────────────

class LiveStartRequest(BaseModel):
    confirm: bool = False
    mode: str = "paper"

class LiveStatusResponse(BaseModel):
    is_running: bool = False
    mode: str = "paper"
    dry_run: bool = True
    uptime_seconds: float = 0
    last_heartbeat: Optional[str] = None
    signals_evaluated: int = 0
    trades_executed: int = 0
    active_positions: list[dict] = []
    enabled_strategies: list[str] = []
    daily_pnl: float = 0.0
    errors: list[str] = []

class EmergencyStopResponse(BaseModel):
    success: bool
    positions_closed: int = 0
    message: str = ""


# ──────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────

class PerformanceReport(BaseModel):
    period: str
    total_pnl: float = 0
    total_trades: int = 0
    win_rate: float = 0
    profit_factor: float = 0
    best_day: float = 0
    worst_day: float = 0
    sharpe: float = 0
    daily_returns: list[dict] = []
    strategy_breakdown: list[dict] = []
    equity_curve: list[dict] = []

class DailyReport(BaseModel):
    date: str
    trades: list[TradeRecord] = []
    total_pnl: float = 0
    win_count: int = 0
    loss_count: int = 0
    signals_generated: int = 0
    signals_filtered: int = 0

class ExportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: str = "csv"  # "csv" | "pdf"


# ──────────────────────────────────────────────
# WebSocket
# ──────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # "price" | "signal" | "trade" | "heartbeat" | "error"
    data: dict
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


# ──────────────────────────────────────────────
# Strategy Info
# ──────────────────────────────────────────────

class StrategyInfo(BaseModel):
    id: int
    name: str
    full_name: str
    category: str = "general"
    description: str = ""
    enabled: bool = True


# ──────────────────────────────────────────────
# Generic
# ──────────────────────────────────────────────

class StatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

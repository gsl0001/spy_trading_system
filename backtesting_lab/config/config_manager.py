"""
Configuration Manager — Loads, validates, and provides runtime access to system config.
Supports YAML file + environment variable overrides.
"""
import os
import yaml
import copy
import json
import datetime
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


# ──────────────────────────────────────────────
# Pydantic Config Models (Validation Layer)
# ──────────────────────────────────────────────

class SystemConfig(BaseModel):
    name: str = "SPY QuantOS"
    version: str = "5.0.0"
    mode: str = Field(default="paper", pattern="^(paper|live|backtest_only)$")
    dry_run: bool = True
    log_level: str = "INFO"

class DataConfig(BaseModel):
    ticker: str = "SPY"
    default_interval: str = "1d"
    history_years: int = 12
    cache_ttl_minutes: int = 15
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    vix_ticker: str = "^VIX"

class StrategiesConfig(BaseModel):
    enabled: list[int] = Field(default_factory=lambda: list(range(1, 38)))
    excluded_from_live: list[int] = Field(default_factory=lambda: [4, 5, 6, 23, 24, 25, 26, 27])

class RiskConfig(BaseModel):
    initial_capital: float = 100000
    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 3.0
    max_open_positions: int = 1
    global_stop_loss_pct: float = 0.0
    global_take_profit_pct: float = 0.0
    trailing_stop_pct: float = 0.0
    max_hold_bars: int = 0
    cooldown_after_loss_minutes: int = 30

class MLConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    confidence_threshold: float = 0.55
    min_trades_for_training: int = 15
    ensemble_min_trades: int = 25
    model_save_path: str = "models/"
    auto_retrain: bool = False
    retrain_schedule_hours: int = 24
    use_ensemble: bool = True

class BrokerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    timeout_seconds: int = 10
    reconnect_attempts: int = 5
    reconnect_delay_seconds: int = 30

class ScheduleConfig(BaseModel):
    market_open: str = "09:30"
    market_close: str = "16:00"
    timezone: str = "America/New_York"
    eval_interval_seconds: int = 60
    pre_market_start: str = "09:15"

class OptionsConfig(BaseModel):
    enabled: bool = False
    default_dte: int = 30
    default_delta: float = 0.50
    asset_class: str = "spot"

class DiscordChannel(BaseModel):
    enabled: bool = True
    webhook_url: str = ""

class EmailChannel(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    to_address: str = ""

class NotificationChannels(BaseModel):
    discord: DiscordChannel = Field(default_factory=DiscordChannel)
    email: EmailChannel = Field(default_factory=EmailChannel)

class NotificationEvents(BaseModel):
    trade_entry: bool = True
    trade_exit: bool = True
    daily_summary: bool = True
    error_alert: bool = True
    system_start: bool = True
    system_stop: bool = True

class NotificationsConfig(BaseModel):
    enabled: bool = True
    channels: NotificationChannels = Field(default_factory=NotificationChannels)
    events: NotificationEvents = Field(default_factory=NotificationEvents)

class ReportingConfig(BaseModel):
    trade_journal_path: str = "data/trade_journal.json"
    reports_output_path: str = "data/reports/"
    auto_daily_report: bool = True
    daily_report_time: str = "16:30"

class AppConfig(BaseModel):
    """Root config model — validates entire configuration tree."""
    system: SystemConfig = Field(default_factory=SystemConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


# ──────────────────────────────────────────────
# Config Manager
# ──────────────────────────────────────────────

class ConfigManager:
    """Singleton-style config manager with YAML + env override support."""

    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    _config_path: Optional[Path] = None
    _history_dir: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None) -> AppConfig:
        """Load config from YAML file with environment variable overrides."""
        if config_path is None:
            # Default: look for config in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "default_config.yaml"
        
        self._config_path = Path(config_path)
        
        # Setup history directory
        self._history_dir = self._config_path.parent / "history"
        self._history_dir.mkdir(parents=True, exist_ok=True)
        
        # Load YAML
        raw_config = {}
        if self._config_path.exists():
            with open(self._config_path, 'r') as f:
                raw_config = yaml.safe_load(f) or {}
            logger.info(f"Config loaded from {self._config_path}")
        else:
            logger.warning(f"Config file not found at {self._config_path}, using defaults")
        
        # Apply environment variable overrides
        raw_config = self._apply_env_overrides(raw_config)
        
        # Validate with Pydantic
        self._config = AppConfig(**raw_config)
        
        # Ensure data directories exist
        self._ensure_directories()
        
        return self._config

    def get(self) -> AppConfig:
        """Get current config. Auto-loads if not yet loaded."""
        if self._config is None:
            self.load()
        return self._config

    def update(self, updates: dict) -> AppConfig:
        """Update config with partial dict. Saves snapshot before applying."""
        if self._config is None:
            self.load()
        
        # Save snapshot
        self._save_snapshot()
        
        # Deep merge updates into current config
        current_dict = self._config.model_dump()
        merged = self._deep_merge(current_dict, updates)
        
        # Re-validate
        self._config = AppConfig(**merged)
        
        # Persist to disk
        self._save_to_disk(merged)
        
        logger.info(f"Config updated: {list(updates.keys())}")
        return self._config

    def reset(self) -> AppConfig:
        """Reset to default config file."""
        self._save_snapshot()
        return self.load()

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get config change history."""
        if not self._history_dir or not self._history_dir.exists():
            return []
        
        snapshots = sorted(self._history_dir.glob("*.json"), reverse=True)[:limit]
        history = []
        for snap in snapshots:
            try:
                with open(snap, 'r') as f:
                    data = json.load(f)
                history.append({
                    "timestamp": snap.stem,
                    "filename": snap.name,
                    "size_bytes": snap.stat().st_size
                })
            except Exception:
                continue
        return history

    def to_dict(self) -> dict:
        """Export current config as dictionary."""
        return self.get().model_dump()

    # ── Private Methods ──

    def _apply_env_overrides(self, config: dict) -> dict:
        """Override config values from environment variables."""
        env_map = {
            ("broker", "host"): "IBKR_HOST",
            ("broker", "port"): "IBKR_PORT",
            ("broker", "client_id"): "IBKR_CLIENT_ID",
            ("system", "mode"): "TRADING_MODE",
            ("notifications", "channels", "discord", "webhook_url"): "DISCORD_WEBHOOK_URL",
            ("notifications", "channels", "email", "smtp_host"): "SMTP_HOST",
            ("notifications", "channels", "email", "smtp_port"): "SMTP_PORT",
            ("notifications", "channels", "email", "username"): "SMTP_USER",
            ("notifications", "channels", "email", "password"): "SMTP_PASSWORD",
            ("notifications", "channels", "email", "to_address"): "ALERT_EMAIL_TO",
        }
        
        for path_tuple, env_key in env_map.items():
            env_val = os.environ.get(env_key)
            if env_val is not None:
                # Navigate to nested dict location and set value
                obj = config
                for key in path_tuple[:-1]:
                    obj = obj.setdefault(key, {})
                
                # Type coerce for int fields
                final_key = path_tuple[-1]
                if final_key in ("port", "client_id", "smtp_port"):
                    env_val = int(env_val)
                
                obj[final_key] = env_val
                logger.debug(f"Config override from env: {'.'.join(path_tuple)} = ***")
        
        return config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dicts. override values win."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save_snapshot(self):
        """Save current config as a timestamped snapshot."""
        if self._config is None or self._history_dir is None:
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self._history_dir / f"{timestamp}.json"
        
        with open(snapshot_path, 'w') as f:
            json.dump(self._config.model_dump(), f, indent=2, default=str)
        
        logger.debug(f"Config snapshot saved: {snapshot_path}")

    def _save_to_disk(self, config_dict: dict):
        """Persist config to YAML file."""
        if self._config_path is None:
            return
        
        with open(self._config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def _ensure_directories(self):
        """Create necessary data directories."""
        if self._config is None:
            return
        
        project_root = Path(__file__).parent.parent
        
        dirs = [
            project_root / self._config.ml.model_save_path,
            project_root / Path(self._config.reporting.trade_journal_path).parent,
            project_root / self._config.reporting.reports_output_path,
        ]
        
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


# Module-level singleton accessor
_manager = ConfigManager()

def get_config() -> AppConfig:
    """Get the global config instance."""
    return _manager.get()

def load_config(path: str = None) -> AppConfig:
    """Load config from file."""
    return _manager.load(path)

def update_config(updates: dict) -> AppConfig:
    """Update config with partial dict."""
    return _manager.update(updates)

def reset_config() -> AppConfig:
    """Reset to defaults."""
    return _manager.reset()

def get_config_manager() -> ConfigManager:
    """Get the ConfigManager singleton."""
    return _manager

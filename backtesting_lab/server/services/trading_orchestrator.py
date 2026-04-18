"""
Trading Orchestrator — Autonomous trading engine with scheduling.
Manages the signal-evaluate-execute loop, position tracking, and system lifecycle.
"""
import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable
from pathlib import Path
from loguru import logger

import pandas as pd
import numpy as np


class TradingOrchestrator:
    """
    Core autonomous engine. Evaluates strategies on schedule,
    filters through ML, and manages position lifecycle.
    """

    def __init__(self, config, ml_filter, journal, notifier):
        self._config = config
        self._ml_filter = ml_filter
        self._journal = journal
        self._notifier = notifier

        # State
        self._is_running = False
        self._start_time = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Metrics
        self._signals_evaluated = 0
        self._trades_executed = 0
        self._daily_pnl = 0.0
        self._errors: list[str] = []
        self._last_heartbeat = None

        # Active positions
        self._positions: list[dict] = []
        self._max_positions = config.risk.max_open_positions

        # Cooldown tracking
        self._last_loss_time = None
        self._cooldown_minutes = config.risk.cooldown_after_loss_minutes

        # Broker connection (lazy init)
        self._ib = None
        self._is_connected = False

    # ── Public API ──

    def start(self, mode: str = "paper") -> dict:
        """Start the autonomous trading loop."""
        if self._is_running:
            return {"success": False, "message": "Already running"}

        # Safety checks
        if mode == "live" and self._config.system.dry_run:
            return {
                "success": False,
                "message": "Cannot start LIVE mode while dry_run is enabled. Update config first."
            }

        self._is_running = True
        self._start_time = time.time()
        self._stop_event.clear()
        self._daily_pnl = 0.0
        self._errors = []

        # Start in background thread
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(mode,),
            daemon=True,
            name="TradingOrchestrator"
        )
        self._thread.start()

        self._notifier.notify_system_event(
            "System Started",
            f"Mode: {mode} | Dry Run: {self._config.system.dry_run}"
        )

        logger.info(f"Trading orchestrator started in {mode} mode")
        return {"success": True, "message": f"Started in {mode} mode"}

    def stop(self) -> dict:
        """Stop the autonomous trading loop gracefully."""
        if not self._is_running:
            return {"success": False, "message": "Not running"}

        self._stop_event.set()
        self._is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        self._notifier.notify_system_event(
            "System Stopped",
            f"Uptime: {self.uptime_seconds:.0f}s | Trades: {self._trades_executed}"
        )

        logger.info("Trading orchestrator stopped")
        return {"success": True, "message": "Stopped"}

    def emergency_stop(self) -> dict:
        """Kill all positions and stop immediately."""
        logger.warning("EMERGENCY STOP triggered")

        positions_closed = len(self._positions)
        self._positions = []
        self.stop()

        self._notifier.notify_error(
            "EMERGENCY STOP ACTIVATED",
            f"Closed {positions_closed} positions"
        )

        return {
            "success": True,
            "positions_closed": positions_closed,
            "message": "Emergency stop executed. All positions closed."
        }

    @property
    def status(self) -> dict:
        """Current system status."""
        return {
            "is_running": self._is_running,
            "mode": self._config.system.mode,
            "dry_run": self._config.system.dry_run,
            "uptime_seconds": self.uptime_seconds,
            "last_heartbeat": self._last_heartbeat,
            "signals_evaluated": self._signals_evaluated,
            "trades_executed": self._trades_executed,
            "active_positions": self._positions.copy(),
            "daily_pnl": round(self._daily_pnl, 2),
            "errors": self._errors[-10:],  # Last 10 errors
        }

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0
        return time.time() - self._start_time

    # ── Core Loop ──

    def _run_loop(self, mode: str):
        """Main execution loop — runs in background thread."""
        interval = self._config.schedule.eval_interval_seconds

        logger.info(f"Evaluation loop started. Interval: {interval}s")

        while not self._stop_event.is_set():
            try:
                self._last_heartbeat = datetime.now().isoformat()

                # Check market hours
                if not self._is_market_hours():
                    self._stop_event.wait(timeout=30)
                    continue

                # Check daily loss limit
                if self._is_daily_loss_exceeded():
                    logger.warning("Daily loss limit reached. Pausing execution.")
                    self._stop_event.wait(timeout=60)
                    continue

                # Check cooldown
                if self._is_in_cooldown():
                    self._stop_event.wait(timeout=30)
                    continue

                # Evaluate signals
                self._evaluate_cycle(mode)
                self._signals_evaluated += 1

            except Exception as e:
                error_msg = f"Loop error: {str(e)}"
                logger.error(error_msg)
                self._errors.append(f"{datetime.now().isoformat()}: {error_msg}")
                self._notifier.notify_error(str(e), "Main evaluation loop")

            # Wait for next cycle
            self._stop_event.wait(timeout=interval)

        logger.info("Evaluation loop exited")

    def _evaluate_cycle(self, mode: str):
        """Single evaluation cycle — fetch data, check signals, manage positions."""
        try:
            # 1. Fetch latest data
            from core.data import fetch_spy_data, preprocess_data, merge_macro_data
            from core.sentiment import get_insider_sentiment
            from core.macro_engine import get_macro_context
            from core.strategies import BacktestEngine

            interval = self._config.data.default_interval
            d_p, d_m, d_v = fetch_spy_data(interval=interval, years=1)
            df = preprocess_data(d_p, d_m, d_v)

            # Merge macro
            macro_df = get_macro_context()
            df = merge_macro_data(df, macro_df)

            # Merge sentiment
            sentiment_df = get_insider_sentiment()
            if not sentiment_df.empty:
                df['temp_date'] = pd.to_datetime(df.index.date)
                sentiment_df.index = pd.to_datetime(sentiment_df.index)
                idx_name = df.index.name or 'Date'
                df = df.reset_index().merge(
                    sentiment_df, left_on='temp_date', right_index=True, how='left'
                ).set_index(idx_name)
                df['Insider_Sentiment'] = df['Insider_Sentiment'].ffill().fillna(1.0)
                df.drop(columns=['temp_date'], inplace=True)
            else:
                df['Insider_Sentiment'] = 1.0

            # 2. Check if we can open a new position
            if len(self._positions) >= self._max_positions:
                # Only manage existing positions
                self._manage_positions(df)
                return

            # 3. Run the AI Selective Master for signal generation
            engine = BacktestEngine(
                df,
                initial_capital=self._config.risk.initial_capital,
                risk_pc=self._config.risk.risk_per_trade_pct,
                ml_filter=self._ml_filter,
                global_stop_loss=self._config.risk.global_stop_loss_pct,
                global_take_profit=self._config.risk.global_take_profit_pct,
                trailing_stop=self._config.risk.trailing_stop_pct,
                max_hold_bars=self._config.risk.max_hold_bars,
            )

            # Get latest bar signals from all enabled strategies
            enabled_ids = self._config.strategies.enabled
            strategy_names = [f"Strategy {i}" for i in enabled_ids]
            signals_df = engine.get_all_signals(strategy_names)

            # Check latest bar
            if signals_df.empty:
                return

            latest_signals = signals_df.iloc[-1]
            active_signals = latest_signals[latest_signals].index.tolist()

            if not active_signals:
                return

            logger.info(f"Active signals at latest bar: {active_signals}")

            # 4. ML Filter
            if self._ml_filter and self._ml_filter.is_trained:
                # Use ensemble if available
                if hasattr(self._ml_filter, 'is_ensemble_trained') and self._ml_filter.is_ensemble_trained:
                    base_feats = df.iloc[-1].reindex(self._ml_filter.base_features).fillna(0)
                    sig_feats = latest_signals.fillna(0)
                    full_feat = pd.concat([base_feats, sig_feats])
                    e_feats = getattr(self._ml_filter, 'ensemble_features', [])
                    model_input = full_feat.reindex(e_feats).fillna(0)
                    prob = self._ml_filter.predict(model_input.values)
                else:
                    feat_row = df.iloc[-1].reindex(self._ml_filter.base_features).fillna(0)
                    prob = self._ml_filter.predict(feat_row.values)

                if prob < self._ml_filter.confidence_threshold:
                    logger.debug(f"ML filter rejected signals. Confidence: {prob:.3f}")
                    return

                logger.info(f"ML filter passed. Confidence: {prob:.3f}")
            else:
                prob = 0.5

            # 5. Pick best strategy (highest trust score if ensemble)
            best_strat = active_signals[0]
            if hasattr(self._ml_filter, 'trust_scores') and self._ml_filter.trust_scores:
                scored = [(s, self._ml_filter.trust_scores.get(s, 0)) for s in active_signals]
                scored.sort(key=lambda x: x[1], reverse=True)
                best_strat = scored[0][0]

            # 6. Execute (or simulate)
            current_price = float(df['Close'].iloc[-1])
            trade_entry = {
                "strategy": best_strat,
                "trade_type": "Long",
                "entry_price": current_price,
                "date_in": datetime.now().isoformat(),
                "ml_confidence": round(float(prob), 3),
                "source": mode,
            }

            if self._config.system.dry_run:
                logger.info(f"[DRY RUN] Would enter: {best_strat} @ ${current_price:.2f}")
                trade_entry["notes"] = "DRY RUN — not executed"
            else:
                logger.info(f"Entering position: {best_strat} @ ${current_price:.2f}")
                # Real broker execution would go here
                self._positions.append(trade_entry)
                self._trades_executed += 1

            # Record and notify
            self._journal.record_trade(trade_entry)
            self._notifier.notify_trade_entry(trade_entry)

        except Exception as e:
            logger.error(f"Evaluation cycle error: {e}")
            self._errors.append(f"{datetime.now().isoformat()}: {str(e)}")

    def _manage_positions(self, df):
        """Check and manage existing positions (exits, stops)."""
        # Placeholder for position management logic
        # In production, this would check stop loss, take profit, trailing stops
        pass

    # ── Guards ──

    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        try:
            import pytz
            tz = pytz.timezone(self._config.schedule.timezone)
            now = datetime.now(tz)
        except Exception:
            now = datetime.now()

        market_open = datetime.strptime(self._config.schedule.market_open, "%H:%M").time()
        market_close = datetime.strptime(self._config.schedule.market_close, "%H:%M").time()

        # Only trade on weekdays
        if now.weekday() >= 5:
            return False

        return market_open <= now.time() <= market_close

    def _is_daily_loss_exceeded(self) -> bool:
        """Check if daily loss limit is reached."""
        max_loss = self._config.risk.initial_capital * (self._config.risk.max_daily_loss_pct / 100)
        return self._daily_pnl <= -max_loss

    def _is_in_cooldown(self) -> bool:
        """Check if we're in post-loss cooldown."""
        if self._last_loss_time is None:
            return False
        elapsed = (datetime.now() - self._last_loss_time).total_seconds() / 60
        return elapsed < self._cooldown_minutes

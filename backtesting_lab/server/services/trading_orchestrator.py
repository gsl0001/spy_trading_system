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
        self._consecutive_losses = 0

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

        # Eagerly connect for live mode to recover state
        if mode == "live":
            logger.info("Initializing IBKR connection for state recovery and live execution...")
            try:
                from ib_insync import IB
                
                # Ensure we have an asyncio loop for this thread (or main thread)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self._ib = IB()
                self._ib.connect(self._config.broker.host, self._config.broker.port, self._config.broker.client_id)
                self._is_connected = True
                
                self._ib.execDetailsEvent += self._on_exec_details
                self._ib.orderStatusEvent += self._on_order_status
                
                # State Recovery
                open_positions = self._ib.positions()
                recovered = 0
                for p in open_positions:
                    if p.contract.secType == 'BAG' and p.contract.symbol == 'SPY':
                        # Reconstruct a basic trade entry
                        trade_entry = {
                            "strategy": "Recovered Position",
                            "trade_type": "Long" if p.position > 0 else "Short",
                            "entry_price": float(p.avgCost), # Assuming BAG avgCost is per spread
                            "date_in": datetime.now().isoformat(), # Approximate
                            "ml_confidence": 1.0,
                            "source": "live",
                            "contract": p.contract,
                            "status": "Recovered"
                        }
                        self._positions.append(trade_entry)
                        recovered += 1
                        
                logger.info(f"Successfully connected to IBKR. Recovered {recovered} open SPY spread positions.")
            except Exception as e:
                logger.error(f"Failed to connect to IBKR or recover state: {e}")
                return {"success": False, "message": f"IBKR Connection failed: {e}"}

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

        # Disconnect from broker if connected
        if self._ib and self._ib.isConnected():
            try:
                self._ib.disconnect()
                self._is_connected = False
                logger.info("Disconnected from IBKR broker.")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {e}")

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
            "consecutive_losses": self._consecutive_losses,
        }

    def get_account_summary(self) -> dict:
        """Fetch real-time account summary from IBKR."""
        if not self._is_connected or not self._ib or not self._ib.isConnected():
            return {"error": "Not connected to IBKR"}
        
        try:
            summary = self._ib.accountSummary()
            # Convert to a flat dict
            data = {item.tag: item.value for item in summary}
            return {
                "NetLiquidation": data.get("NetLiquidation", "0"),
                "TotalCashValue": data.get("TotalCashValue", "0"),
                "SettledCash": data.get("SettledCash", "0"),
                "BuyingPower": data.get("BuyingPower", "0"),
                "InitMarginReq": data.get("InitMarginReq", "0"),
                "MaintMarginReq": data.get("MaintMarginReq", "0"),
                "ExcessLiquidity": data.get("ExcessLiquidity", "0"),
                "Currency": data.get("Currency", "USD")
            }
        except Exception as e:
            return {"error": str(e)}

    def get_live_positions(self) -> list:
        """Fetch real-time positions from IBKR."""
        if not self._is_connected or not self._ib or not self._ib.isConnected():
            return []
        
        try:
            positions = self._ib.positions()
            results = []
            for p in positions:
                results.append({
                    "symbol": p.contract.symbol,
                    "secType": p.contract.secType,
                    "position": p.position,
                    "avgCost": p.avgCost,
                    "contract": str(p.contract)
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching live positions: {e}")
            return []

    def get_live_orders(self) -> list:
        """Fetch real-time active trades/orders from IBKR."""
        if not self._is_connected or not self._ib or not self._ib.isConnected():
            return []
        
        try:
            trades = self._ib.trades()
            results = []
            for t in trades:
                results.append({
                    "orderId": t.order.orderId,
                    "symbol": t.contract.symbol,
                    "action": t.order.action,
                    "orderType": t.order.orderType,
                    "totalQuantity": t.order.totalQuantity,
                    "lmtPrice": t.order.lmtPrice,
                    "status": t.orderStatus.status,
                    "filled": t.orderStatus.filled,
                    "remaining": t.orderStatus.remaining,
                    "avgFillPrice": t.orderStatus.avgFillPrice
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching live orders: {e}")
            return []

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

            # 2. Manage existing positions
            self._manage_positions(df)
            
            if len(self._positions) >= self._max_positions:
                return

            if self._consecutive_losses >= 3:
                logger.warning("Circuit Breaker Active: 3 consecutive losses hit. Blocking new trades.")
                return

            # Volatility Sizing Adjustment
            current_risk_pc = self._config.risk.risk_per_trade_pct
            if 'VIX_Close' in df.columns and float(df['VIX_Close'].iloc[-1]) > 30.0:
                current_risk_pc = current_risk_pc / 2
                logger.info(f"High VIX detected (>30). Risk per trade halved to {current_risk_pc}%")

            # 3. Run the AI Selective Master for signal generation
            engine = BacktestEngine(
                df,
                initial_capital=self._config.risk.initial_capital,
                risk_pc=current_risk_pc,
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
                
                # Real broker execution
                if mode == "live":
                    if not self._is_connected or not self._ib.isConnected():
                        logger.error("IBKR is disconnected. Aborting live execution.")
                        self._errors.append(f"{datetime.now().isoformat()}: IBKR Disconnected")
                        return

                    try:
                        from live_trading_hub.execution_engine import ExecutionEngine
                        engine = ExecutionEngine(self._ib)
                        # We use run_until_complete since execute_combo is async
                        direction = "LONG" if "Bull Put" in best_strat or "Long" in trade_entry["trade_type"] else "SHORT"
                        
                        loop = asyncio.get_event_loop()
                        trade = loop.run_until_complete(engine.execute_combo(direction, current_price))
                        
                        if trade:
                            logger.info(f"Live execution submitted. Order ID: {trade.order.orderId}")
                            trade_entry["notes"] = "LIVE EXECUTED via IBKR 0DTE Spread"
                            trade_entry["trade_obj"] = trade
                            trade_entry["contract"] = trade.contract
                            trade_entry["status"] = trade.orderStatus.status
                        else:
                            logger.warning("Live execution reported failure or no bid/ask.")
                            trade_entry["notes"] = "LIVE EXECUTION FAILED"
                    except Exception as e:
                        logger.error(f"Live execution error: {e}")
                        self._errors.append(f"{datetime.now().isoformat()}: Execution Error - {e}")
                        trade_entry["notes"] = f"LIVE EXECUTION ERROR: {e}"

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
        if not self._positions:
            return

        current_price = float(df['Close'].iloc[-1])
        
        # Initialize engine for exit logic
        from core.strategies import BacktestEngine
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

        # Check for Market On Close (MOC) Time Stop
        import pytz
        tz = pytz.timezone(self._config.schedule.timezone)
        now_est = datetime.now(tz).time()
        moc_time = datetime.strptime("15:45", "%H:%M").time()
        force_moc_exit = now_est >= moc_time

        for pos in self._positions[:]:  # Iterate over copy to allow removal
            entry_price = pos.get("entry_price")
            pnl_pct = (current_price - entry_price) / entry_price if pos.get("trade_type") == "Long" else (entry_price - current_price) / entry_price
            
            trigger_exit = False
            reason = ""
            exit_price = current_price

            if force_moc_exit:
                trigger_exit = True
                reason = "Market-On-Close Time Stop (15:45 EST)"
            else:
                # 1. Strategy Exit Signal
                best_strat = pos.get("strategy")
                exit_logic = engine.run_strategy(best_strat, return_logic=True)
                
                if exit_logic:
                    try:
                        # Find entry_idx in current df based on pos["date_in"]
                        entry_dt = pd.to_datetime(pos["date_in"])
                        # Use nearest or exact match. Data might have changed slightly.
                        entry_idx = df.index.get_indexer([entry_dt], method='nearest')[0]
                        curr_idx = len(df) - 1
                        
                        strat_exit, strat_exit_price = exit_logic(df, curr_idx, entry_price, entry_idx)
                        if strat_exit:
                            trigger_exit = True
                            reason = f"Strategy Exit Signal: {best_strat}"
                            exit_price = strat_exit_price if strat_exit_price > 0 else current_price
                    except Exception as e:
                        logger.error(f"Error evaluating exit logic for {best_strat}: {e}")

                # 2. Global SL/TP (Overrides)
                if not trigger_exit:
                    sl = self._config.risk.global_stop_loss_pct / 100
                    tp = self._config.risk.global_take_profit_pct / 100
                    
                    if pnl_pct <= -sl:
                        trigger_exit = True
                        reason = f"Global Stop Loss hit: {pnl_pct*100:.2f}%"
                    elif pnl_pct >= tp:
                        trigger_exit = True
                        reason = f"Global Take Profit hit: {pnl_pct*100:.2f}%"
            
            if trigger_exit:
                logger.info(f"Triggering exit for {pos['strategy']}: {reason}")
                if pos.get("source") == "live" and self._is_connected and self._ib.isConnected():
                    try:
                        from live_trading_hub.execution_engine import ExecutionEngine
                        exec_engine = ExecutionEngine(self._ib)
                        loop = asyncio.get_event_loop()
                        close_trade = loop.run_until_complete(exec_engine.close_position(pos["contract"]))
                        if close_trade:
                            pos["status"] = "Closing"
                            pos["close_trade_obj"] = close_trade
                    except Exception as e:
                        logger.error(f"Error closing live position: {e}")
                
                # Update position state
                pos["date_out"] = datetime.now().isoformat()
                pos["exit_price"] = exit_price
                pos["pnl"] = round(pnl_pct, 4)
                pos["exit_reason"] = reason
                
                # Update consecutive loss tracking
                if pnl_pct < 0:
                    self._consecutive_losses += 1
                    self._last_loss_time = datetime.now()
                    logger.warning(f"Trade closed for loss. Consecutive losses: {self._consecutive_losses}")
                else:
                    self._consecutive_losses = 0
                
                # Record and notify
                self._journal.record_trade(pos)
                self._notifier.notify_trade_exit(pos)
                self._positions.remove(pos)

    def _on_exec_details(self, trade, fill):
        """Handle execution details (fills) from IBKR."""
        logger.info(f"IBKR FILL: {trade.contract.symbol} {fill.execution.side} {fill.execution.shares} @ {fill.execution.avgPrice}")
        for pos in self._positions:
            if pos.get("trade_obj") == trade or pos.get("close_trade_obj") == trade:
                pos["status"] = "Filled"
                pos["fill_price"] = fill.execution.avgPrice
                if pos.get("close_trade_obj") == trade:
                    pos["exit_price"] = fill.execution.avgPrice
                break

    def _on_order_status(self, trade):
        """Handle order status changes from IBKR."""
        logger.debug(f"IBKR ORDER STATUS: {trade.contract.symbol} -> {trade.orderStatus.status}")
        for pos in self._positions:
            if pos.get("trade_obj") == trade or pos.get("close_trade_obj") == trade:
                pos["status"] = trade.orderStatus.status
                break

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

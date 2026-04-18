"""
Trade Journal — Persistent, append-only trade log with JSON storage.
Records every trade event for historical analysis and reporting.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


class TradeJournal:
    """Append-only trade journal backed by a JSON file."""

    def __init__(self, journal_path: str = "data/trade_journal.json"):
        self._path = Path(journal_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._trades: list[dict] = []
        self._load()

    def _load(self):
        """Load existing journal from disk."""
        if self._path.exists():
            try:
                with open(self._path, 'r') as f:
                    self._trades = json.load(f)
                logger.info(f"Trade journal loaded: {len(self._trades)} records from {self._path}")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load trade journal, starting fresh: {e}")
                self._trades = []
        else:
            self._trades = []
            logger.info(f"New trade journal initialized at {self._path}")

    def _save(self):
        """Persist journal to disk."""
        try:
            with open(self._path, 'w') as f:
                json.dump(self._trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save trade journal: {e}")

    def record_trade(self, trade: dict) -> dict:
        """Record a completed trade. Adds metadata and persists."""
        record = {
            "id": len(self._trades) + 1,
            "recorded_at": datetime.now().isoformat(),
            "strategy": trade.get("strategy", "Unknown"),
            "date_in": str(trade.get("date_in", trade.get("Date In", ""))),
            "date_out": str(trade.get("date_out", trade.get("Date Out", ""))),
            "trade_type": trade.get("trade_type", trade.get("Type", "Long")),
            "entry_price": float(trade.get("entry_price", trade.get("Entry Price", 0))),
            "exit_price": float(trade.get("exit_price", trade.get("Exit Price", 0))),
            "pnl": float(trade.get("pnl", trade.get("PnL", 0))),
            "pnl_pct": float(trade.get("pnl_pct", trade.get("PnL %", 0))),
            "duration": trade.get("duration", trade.get("Duration", None)),
            "ml_confidence": trade.get("ml_confidence", None),
            "regime": trade.get("regime", None),
            "source": trade.get("source", "backtest"),  # "backtest" | "live" | "paper"
            "notes": trade.get("notes", ""),
        }

        self._trades.append(record)
        self._save()
        logger.info(f"Trade #{record['id']} recorded: {record['strategy']} | PnL: {record['pnl']:.2f}")
        return record

    def record_batch(self, trades_df) -> int:
        """Record a batch of trades from a DataFrame (backtest results)."""
        count = 0
        for _, row in trades_df.iterrows():
            self.record_trade(row.to_dict())
            count += 1
        logger.info(f"Batch recorded: {count} trades")
        return count

    def get_trades(self, start_date: str = None, end_date: str = None,
                   strategy: str = None, source: str = None,
                   limit: int = 500) -> list[dict]:
        """Query trades with optional filters."""
        results = self._trades.copy()

        if source:
            results = [t for t in results if t.get("source") == source]

        if strategy:
            results = [t for t in results if strategy.lower() in t.get("strategy", "").lower()]

        if start_date:
            results = [t for t in results if t.get("date_in", "") >= start_date]

        if end_date:
            results = [t for t in results if t.get("date_out", "") <= end_date]

        # Return most recent first, limited
        return list(reversed(results[-limit:]))

    def get_daily_summary(self, date_str: str = None) -> dict:
        """Get summary for a specific date (default: today)."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        day_trades = [t for t in self._trades if date_str in t.get("date_out", "")]

        wins = [t for t in day_trades if t.get("pnl", 0) > 0]
        losses = [t for t in day_trades if t.get("pnl", 0) <= 0]

        return {
            "date": date_str,
            "total_trades": len(day_trades),
            "wins": len(wins),
            "losses": len(losses),
            "total_pnl": sum(t.get("pnl", 0) for t in day_trades),
            "win_rate": len(wins) / len(day_trades) * 100 if day_trades else 0,
            "best_trade": max((t.get("pnl", 0) for t in day_trades), default=0),
            "worst_trade": min((t.get("pnl", 0) for t in day_trades), default=0),
            "trades": day_trades,
        }

    def get_strategy_performance(self) -> list[dict]:
        """Performance breakdown by strategy."""
        strat_map = {}
        for t in self._trades:
            s = t.get("strategy", "Unknown")
            if s not in strat_map:
                strat_map[s] = {"strategy": s, "trades": 0, "wins": 0, "total_pnl": 0}
            strat_map[s]["trades"] += 1
            strat_map[s]["total_pnl"] += t.get("pnl", 0)
            if t.get("pnl", 0) > 0:
                strat_map[s]["wins"] += 1

        result = []
        for s, data in strat_map.items():
            data["win_rate"] = round(data["wins"] / data["trades"] * 100, 1) if data["trades"] > 0 else 0
            data["avg_pnl"] = round(data["total_pnl"] / data["trades"], 2) if data["trades"] > 0 else 0
            result.append(data)

        return sorted(result, key=lambda x: x["total_pnl"], reverse=True)

    @property
    def total_trades(self) -> int:
        return len(self._trades)

    @property
    def live_trades(self) -> list[dict]:
        return [t for t in self._trades if t.get("source") in ("live", "paper")]

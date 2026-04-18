"""
Report Generator — Builds performance reports from trade journal data.
Generates daily summaries, period analytics, and strategy attribution.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from loguru import logger


class ReportGenerator:
    """Generates performance reports from trade journal data."""

    def __init__(self, journal, output_path: str = "data/reports/"):
        self._journal = journal
        self._output_path = Path(output_path)
        self._output_path.mkdir(parents=True, exist_ok=True)

    def daily_report(self, date_str: str = None) -> dict:
        """Generate a daily performance report."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        summary = self._journal.get_daily_summary(date_str)
        
        return {
            "type": "daily",
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "total_trades": summary["total_trades"],
            "wins": summary["wins"],
            "losses": summary["losses"],
            "total_pnl": round(summary["total_pnl"], 2),
            "win_rate": round(summary["win_rate"], 1),
            "best_trade": round(summary["best_trade"], 2),
            "worst_trade": round(summary["worst_trade"], 2),
            "trades": summary["trades"],
        }

    def performance_report(self, period: str = "30d") -> dict:
        """Generate a performance report for a given period."""
        # Parse period
        days = self._parse_period(period)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        trades = self._journal.get_trades(start_date=start_str, end_date=end_str)
        
        if not trades:
            return {
                "type": "performance",
                "period": period,
                "start_date": start_str,
                "end_date": end_str,
                "total_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "sharpe": 0,
                "daily_returns": [],
                "strategy_breakdown": [],
                "equity_curve": [],
            }

        # Calculate metrics
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) <= 0]
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        win_rate = len(wins) / len(trades) * 100 if trades else 0

        gross_profit = sum(t.get("pnl", 0) for t in wins)
        gross_loss = abs(sum(t.get("pnl", 0) for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

        # Daily returns aggregation
        daily_pnl = {}
        for t in trades:
            date_key = str(t.get("date_out", ""))[:10]
            if date_key not in daily_pnl:
                daily_pnl[date_key] = 0
            daily_pnl[date_key] += t.get("pnl", 0)

        daily_returns = [{"date": k, "pnl": round(v, 2)} for k, v in sorted(daily_pnl.items())]

        # Cumulative equity curve
        equity = []
        cumulative = 0
        for dr in daily_returns:
            cumulative += dr["pnl"]
            equity.append({"date": dr["date"], "value": round(cumulative, 2)})

        # Best/worst days
        pnl_values = [dr["pnl"] for dr in daily_returns] if daily_returns else [0]
        best_day = max(pnl_values)
        worst_day = min(pnl_values)

        # Sharpe approximation (daily)
        import numpy as np
        if len(pnl_values) > 1:
            returns = np.array(pnl_values)
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0

        # Strategy breakdown
        strategy_breakdown = self._journal.get_strategy_performance()

        return {
            "type": "performance",
            "period": period,
            "start_date": start_str,
            "end_date": end_str,
            "generated_at": datetime.now().isoformat(),
            "total_trades": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(float(profit_factor), 2),
            "best_day": round(best_day, 2),
            "worst_day": round(worst_day, 2),
            "sharpe": round(float(sharpe), 2),
            "daily_returns": daily_returns,
            "strategy_breakdown": strategy_breakdown,
            "equity_curve": equity,
        }

    def export_csv(self, start_date: str = None, end_date: str = None) -> str:
        """Export trades as CSV string."""
        trades = self._journal.get_trades(start_date=start_date, end_date=end_date, limit=10000)
        
        if not trades:
            return "No trades found for the specified period."

        # Build CSV
        headers = ["id", "recorded_at", "strategy", "date_in", "date_out", 
                    "trade_type", "entry_price", "exit_price", "pnl", "pnl_pct", 
                    "duration", "source"]
        
        lines = [",".join(headers)]
        for t in trades:
            row = [str(t.get(h, "")) for h in headers]
            lines.append(",".join(row))

        csv_content = "\n".join(lines)
        
        # Save to disk
        filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self._output_path / filename
        with open(filepath, 'w') as f:
            f.write(csv_content)
        
        logger.info(f"CSV export saved: {filepath}")
        return csv_content

    def save_report(self, report: dict, report_type: str = "daily") -> str:
        """Save a report to disk as JSON."""
        filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self._output_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved: {filepath}")
        return str(filepath)

    def _parse_period(self, period: str) -> int:
        """Parse period string (e.g. '30d', '7d', '90d') to days."""
        period = period.strip().lower()
        if period.endswith('d'):
            return int(period[:-1])
        elif period.endswith('w'):
            return int(period[:-1]) * 7
        elif period.endswith('m'):
            return int(period[:-1]) * 30
        elif period.endswith('y'):
            return int(period[:-1]) * 365
        else:
            try:
                return int(period)
            except ValueError:
                return 30

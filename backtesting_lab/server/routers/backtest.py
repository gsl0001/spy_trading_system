"""
Backtest API Router — Endpoints for running and managing backtests.
"""
import sys
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backtesting_lab.server.models import BacktestRequest, BacktestResponse, BacktestMetrics, TradeRecord, StrategyInfo

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

# Strategy catalog
STRATEGY_CATALOG = [
    StrategyInfo(id=1, name="20/50 Trend Pullback", full_name="Strategy 1: 20/50 Trend Pullback", category="trend"),
    StrategyInfo(id=2, name="Range Breakout", full_name="Strategy 2: Range Breakout", category="breakout"),
    StrategyInfo(id=3, name="Mean Reversion", full_name="Strategy 3: Mean Reversion", category="mean_reversion"),
    StrategyInfo(id=4, name="Bull Put Spread (Syn)", full_name="Strategy 4: Bull Put Spread (Syn)", category="options"),
    StrategyInfo(id=5, name="Bear Call Spread (Syn)", full_name="Strategy 5: Bear Call Spread (Syn)", category="options"),
    StrategyInfo(id=6, name="Iron Condor (Syn)", full_name="Strategy 6: Iron Condor (Syn)", category="options"),
    StrategyInfo(id=7, name="Inside-Bar Breakout", full_name="Strategy 7: Inside-Bar Breakout", category="breakout"),
    StrategyInfo(id=8, name="3-Day Pullback", full_name="Strategy 8: 3-Day Pullback", category="trend"),
    StrategyInfo(id=9, name="Fade Strategy 4", full_name="Strategy 9: Fade Strategy 4", category="mean_reversion"),
    StrategyInfo(id=10, name="Insider Alpha", full_name="Strategy 10: Insider Alpha (Smart Money)", category="sentiment"),
    StrategyInfo(id=11, name="Combo Alpha", full_name="Strategy 11: Combo Alpha (Multi-Signal)", category="multi"),
    StrategyInfo(id=12, name="Streak Follower", full_name="Strategy 12: Streak Follower", category="behavioral"),
    StrategyInfo(id=13, name="SuperTrend Follower", full_name="Strategy 13: SuperTrend Follower", category="trend"),
    StrategyInfo(id=14, name="Ichimoku Cloud Breakout", full_name="Strategy 14: Ichimoku Cloud Breakout", category="trend"),
    StrategyInfo(id=15, name="EMA Ribbon Expansion", full_name="Strategy 15: EMA Ribbon Expansion", category="trend"),
    StrategyInfo(id=16, name="Donchian 20-Day Breakout", full_name="Strategy 16: Donchian 20-Day Breakout", category="breakout"),
    StrategyInfo(id=17, name="HMA Slope Pivot", full_name="Strategy 17: HMA Slope Pivot", category="momentum"),
    StrategyInfo(id=18, name="Stochastic RS Fade", full_name="Strategy 18: Stochastic RS Fade", category="mean_reversion"),
    StrategyInfo(id=19, name="Fisher Transform Reversal", full_name="Strategy 19: Fisher Transform Reversal", category="reversal"),
    StrategyInfo(id=20, name="Parabolic SAR Flip", full_name="Strategy 20: Parabolic SAR Flip", category="trend"),
    StrategyInfo(id=21, name="Volatility Squeeze Breakout", full_name="Strategy 21: Volatility Squeeze Breakout", category="breakout"),
    StrategyInfo(id=22, name="Money Flow Index (MFI)", full_name="Strategy 22: Money Flow Index (MFI)", category="flow"),
    StrategyInfo(id=23, name="ORB (30-min Approx)", full_name="Strategy 23: ORB (30-min Approximation)", category="intraday"),
    StrategyInfo(id=24, name="Gap-and-Go", full_name="Strategy 24: Gap-and-Go", category="intraday"),
    StrategyInfo(id=25, name="Gap Fade", full_name="Strategy 25: Gap Fade", category="intraday"),
    StrategyInfo(id=26, name="Turnaround Tuesday", full_name="Strategy 26: Turnaround Tuesday", category="calendar"),
    StrategyInfo(id=27, name="Friday Afternoon Squeeze", full_name="Strategy 27: Friday Afternoon Squeeze", category="calendar"),
    StrategyInfo(id=28, name="Pivot Point Bounce", full_name="Strategy 28: Pivot Point Bounce", category="support"),
    StrategyInfo(id=29, name="MTF RSI Alignment", full_name="Strategy 29: MTF RSI Alignment", category="momentum"),
    StrategyInfo(id=30, name="Heikin Ashi Rider", full_name="Strategy 30: Heikin Ashi Rider", category="trend"),
    StrategyInfo(id=31, name="Volatility Spike Fade", full_name="Strategy 31: Volatility Spike Fade", category="volatility"),
    StrategyInfo(id=32, name="Z-Score Mean Reversion", full_name="Strategy 32: Mean Reversion (v2)", category="mean_reversion"),
    StrategyInfo(id=33, name="Yield Curve Regime", full_name="Strategy 33: Yield Curve Regime Filter", category="macro"),
    StrategyInfo(id=34, name="VIX Spike MR", full_name="Strategy 34: VIX Spike Mean Reversion", category="volatility"),
    StrategyInfo(id=35, name="Monetary Policy Pivot", full_name="Strategy 35: Monetary Policy Pivot", category="macro"),
    StrategyInfo(id=36, name="AI Meta-Ensemble", full_name="Strategy 36: AI Meta-Ensemble", category="ai"),
    StrategyInfo(id=37, name="VWAP-Keltner Compression", full_name="Strategy 37: VWAP-Keltner Compression Breakout", category="breakout"),
    StrategyInfo(id=38, name="Selective Master Orchestrator", full_name="Strategy 38: Selective Master Orchestrator", category="multi"),
]


@router.get("/strategies", response_model=list[StrategyInfo])
async def list_strategies():
    """List all available strategies with metadata."""
    return STRATEGY_CATALOG


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest):
    """Execute a backtest with the given parameters."""
    try:
        from core.data import fetch_spy_data, preprocess_data, merge_macro_data
        from core.strategies import BacktestEngine
        from core.options_engine import OptionsBacktestEngine
        from core.sentiment import get_insider_sentiment
        from core.macro_engine import get_macro_context
        from core.ml_engine import MLEnsembleFilter

        # Resolve dates
        end_date = datetime.strptime(req.end_date, "%Y-%m-%d").date() if req.end_date else datetime.now().date()
        start_date = datetime.strptime(req.start_date, "%Y-%m-%d").date() if req.start_date else (end_date - timedelta(days=365))

        # Fetch data
        d_p, d_m, d_v = fetch_spy_data(interval=req.interval, years=12)
        df_all = preprocess_data(d_p, d_m, d_v)

        # Merge macro
        macro_df = get_macro_context()
        df_all = merge_macro_data(df_all, macro_df)

        import pandas as pd
        
        # Merge sentiment
        sentiment_df = get_insider_sentiment()
        if not sentiment_df.empty:
            df_all['temp_date'] = pd.to_datetime(df_all.index.date)
            sentiment_df.index = pd.to_datetime(sentiment_df.index)
            idx_name = df_all.index.name or 'Date'
            df_all = df_all.reset_index().merge(
                sentiment_df, left_on='temp_date', right_index=True, how='left'
            ).set_index(idx_name)
            df_all['Insider_Sentiment'] = df_all['Insider_Sentiment'].ffill().fillna(1.0)
            df_all.drop(columns=['temp_date'], inplace=True)
        else:
            df_all['Insider_Sentiment'] = 1.0

        # Filter date range
        df = df_all.loc[(df_all.index.date >= start_date) & (df_all.index.date <= end_date)].copy()

        if df.empty:
            raise HTTPException(status_code=400, detail="No data for selected date range")

        # Build engine
        EngineClass = OptionsBacktestEngine if req.asset_class == "options" else BacktestEngine
        engine_kwargs = {
            "initial_capital": req.initial_capital,
            "risk_pc": req.risk_pct,
            "global_stop_loss": req.global_stop_loss,
            "global_take_profit": req.global_take_profit,
            "trailing_stop": req.trailing_stop,
            "max_hold_bars": req.max_hold_bars,
        }
        if req.asset_class == "options":
            engine_kwargs["target_dte"] = req.target_dte
            engine_kwargs["target_delta"] = req.target_delta

        engine = EngineClass(df, **engine_kwargs)

        # Execute strategy
        collisions = 0
        strategy_name = req.strategy

        if "Selective Master" in strategy_name:
            strategy_options = [s.full_name for s in STRATEGY_CATALOG if "Orchestrator" not in s.full_name]
            trades_res, equity_res, collisions = engine.run_ai_selective_master(strategy_options)
        elif "Portfolio" in strategy_name:
            base_strats = [s.full_name for s in STRATEGY_CATALOG if s.id != 36]
            res = [engine.run_strategy(s, use_ml=req.use_ml) for s in base_strats]
            trades_res = pd.concat([r[0] for r in res]).sort_values("Date In") if not all(r[0].empty for r in res) else pd.DataFrame()
            equity_res = pd.concat([r[1] for r in res], axis=1).mean(axis=1)
        else:
            trades_res, equity_res = engine.run_strategy(strategy_name, use_ml=req.use_ml)

        # Calculate metrics
        metrics_dict = engine._calculate_metrics(trades_res, equity_res)

        # Format trades
        trades_list = []
        if not trades_res.empty:
            for _, row in trades_res.iterrows():
                trades_list.append(TradeRecord(
                    strategy=str(row.get("Strategy", "")),
                    date_in=str(row["Date In"]),
                    date_out=str(row["Date Out"]),
                    trade_type=str(row.get("Type", "Long")),
                    entry_price=float(row["Entry Price"]),
                    exit_price=float(row["Exit Price"]),
                    pnl=float(row["PnL"]),
                    pnl_pct=float(row["PnL %"]),
                    duration=int(row.get("Duration", 0)) if "Duration" in row else None,
                ))

        # Format equity curve
        equity_data = []
        for idx, val in equity_res.items():
            time_val = idx.strftime('%Y-%m-%d') if req.interval == "1d" else str(idx)
            equity_data.append({"time": time_val, "value": round(float(val), 2)})

        return BacktestResponse(
            success=True,
            strategy=strategy_name,
            metrics=BacktestMetrics(
                total_return_pct=metrics_dict["Total Return %"],
                max_drawdown_pct=metrics_dict["Max Drawdown %"],
                win_rate_pct=metrics_dict["Win Rate %"],
                profit_factor=metrics_dict["Profit Factor"],
                sharpe_ratio=metrics_dict["Sharpe Ratio"],
                sortino_ratio=metrics_dict["Sortino Ratio"],
                trade_count=metrics_dict["Trade Count"],
                expectancy=metrics_dict["Expectancy"],
                recovery_factor=metrics_dict["Recovery Factor"],
                avg_win=metrics_dict["Avg Win"],
                avg_loss=metrics_dict["Avg Loss"],
                payoff_ratio=metrics_dict["Payoff Ratio"],
                max_consecutive_wins=metrics_dict["Max Consecutive Wins"],
                max_consecutive_losses=metrics_dict["Max Consecutive Losses"],
            ),
            trades=trades_list,
            equity_curve=equity_data,
            collisions=collisions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return BacktestResponse(
            success=False,
            strategy=req.strategy,
            metrics=BacktestMetrics(),
            trades=[],
            equity_curve=[],
            error=str(e),
        )

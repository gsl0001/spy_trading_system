# SPY Backtesting Engine & Dashboard Implementation Plan

## Goal Description
Build a professional-grade Python-based backtesting engine for 8 SPY daily trading strategies with an interactive Streamlit dashboard.

## Proposed Changes

### 1. Data Acquisition & Preprocessing (`data.py`) [MODIFY]
- **Fetch**: 10 years of SPY daily data using `yfinance`.
- **Indicators**:
    - SMA 20, 50.
    - VWAP Proxy (Rolling typical price * volume sum / volume sum).
    - Donchian Channels (10-day and 20-day).
    - ATR (14-day).
    - Historical Volatility (252-day annualized).
- **Patterns**:
    - Bullish/Bearish Reversal Candle detection.
    - Inside Bar detection.
    - Mother Bar detection (for Strategy 7).

### 2. Strategy Implementation (`strategies.py`) [MODIFY]
Implement 8 strategies using `vectorbt` for performance, with pre-calculated entry/exit signals for complex logic:
- **Strategy 1**: Trend Pullback (SMA 20/50 + Bullish Cluster).
- **Strategy 2**: Range Breakout (Donchian High + Volume).
- **Strategy 3**: Mean Reversion (Extreme stretch below SMA 20 + Reversal).
- **Strategy 4**: Bull Put Spread Simulation (Synthetic).
- **Strategy 5**: Bear Call Spread Simulation (Synthetic).
- **Strategy 6**: Iron Condor Simulation (Synthetic).
- **Strategy 7**: Daily Inside-Bar Breakout (Break of Mother Bar).
- **Strategy 8**: 3-Day Pullback (Uptrend + 3 bearish days + Bullish day).

### 3. Streamlit Dashboard (`app.py`) [NEW]
- **Sidebar**: Date selectors, strategy dropdown, capital allocation.
- **KPIs**: Total Return, Max Drawdown, Win Rate, Profit Factor, Sharpe Ratio.
- **Charts**:
    - Candlestick (Plotly) + Strategy Markers + Indicators.
    - Equity Curve (Plotly) vs Buy & Hold.
- **Trade Log**: Paginated dataframe showing execution details.

## Open Questions
- **Benchmark**: Should the Buy & Hold benchmark also start with the same initial capital and consider fees? (Default: Yes).
- **Portfolio Mode**: When "Portfolio" is selected, should it be a simple equal-weighted combination of all strategies? (Default: Yes).
- **Risk per Trade**: How should "Risk % per trade" be applied? (Default: Used for position sizing based on ATR stop distance if applicable, otherwise fixed % of equity).

## Verification Plan

### Automated Tests
- Script to run each strategy independently and verify return objects have expected columns (Equity, Trades).
- Validation of indicator calculations against known `pandas_ta` outputs.

### Manual Verification
- Run `streamlit run app.py` and interact with the UI.
- Verify trade markers align with strategy logic on the candlestick chart.
- Compare benchmark curve with SPY price movement.

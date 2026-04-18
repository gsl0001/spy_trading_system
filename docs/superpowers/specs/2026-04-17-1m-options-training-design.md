# 1-Minute 0DTE Options Training & Deployment Architecture

## Goal
Streamline the project to train an AI model (XGBoost) on the SPY underlying 1-minute data using the VWAP Keltner Compression Breakout strategy (Strategy 37), and seamlessly deploy this model to the `live_trading_hub` for 0DTE options execution.

## Architecture & Data Flow

### 1. Unified Shared Model Directory
- Create a `core/models/` directory to act as the single source of truth for trained AI models.
- **Benefit:** `backtesting_lab` writes models here, and `live_trading_hub` reads them from here, preventing file duplication and synchronization issues.

### 2. Dashboard Integration (`backtesting_lab`)
- Add a new "0DTE Live Model Training" action to the Streamlit sidebar in `app.py` or a dedicated UI section.
- **Execution Flow:**
  1. Fetch high-resolution 1-minute SPY data (up to 7 days via `yfinance` or a suitable provider).
  2. Compute technical indicators: VWAP, Keltner Channels, MACD, and CMF.
  3. Execute a localized backtest on this 1m data using **Strategy 37 (VWAP Keltner Breakout)** to identify historical triggers and their success/failure (PnL).
  4. Extract normalized feature vectors (`['MACD_Hist_Dist', 'CMF', 'VWAP_Proxy_Dist']`) for each trade.
  5. Train the XGBoost classifier (Meta-Learner) to predict the probability of a trade being successful.
  6. Serialize and save the trained model to `core/models/my_0dte_model.pkl`.

### 3. Streamlined Live Trading Hub (`live_trading_hub`)
- Update `live_trading_hub/strategy_engine.py` to load the model from the shared `core/models/my_0dte_model.pkl` path.
- **Data Normalization:** Update the live data streamer and the strategy engine to feed the exact same feature columns and scaling as the training data (e.g., converting absolute `VWAP_Proxy` to a percentage distance `VWAP_Proxy_Dist`).
- **Execution:** Ensure `live_trading_hub/execution_engine.py` constructs Bull Put / Bear Call credit spreads based on the AI's confidence score surpassing the `ai_threshold`.

## Components to Modify

1. **`core/data.py`**:
   - Ensure indicator calculation supports 1-minute data frequency gracefully (e.g., ATR window adjustments if necessary).
   - Ensure the creation of the `VWAP_Proxy_Dist` column.

2. **`core/ml_engine.py`**:
   - Add a specialized training path or configuration for the 1-minute 0DTE model that focuses strictly on the 3 feature vectors rather than the 52-dimensional daily ensemble.

3. **`backtesting_lab/app.py`**:
   - Introduce the UI trigger for the 1m model training.
   - Display a success message or training metrics upon completion.

4. **`live_trading_hub/strategy_engine.py`**:
   - Refactor `_get_ai_trust()` to use `VWAP_Proxy_Dist`.
   - Update model loading path to `../core/models/my_0dte_model.pkl`.

## Risks & Mitigations
- **Feature Mismatch:** If the live data streamer calculates MACD or VWAP slightly differently than the historical data fetcher, the model will perform poorly. **Mitigation:** Both systems must route their raw data through the exact same `preprocess_data` function in `core/data.py`.
- **YFinance 1m Limits:** Yahoo Finance restricts 1m data to the last 7 days. **Mitigation:** The training script must handle this gracefully, ensuring enough signals occur in that 7-day window to train a basic Random Forest/XGBoost, or require a premium data feed in the future.

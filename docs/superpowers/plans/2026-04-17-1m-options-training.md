# 1m Options Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the training and deployment pipeline for a 1-minute 0DTE options model using the VWAP Keltner Breakout strategy.

**Architecture:** We will create a shared `core/models` directory. We will update `core/data.py` to calculate `VWAP_Proxy_Dist` properly for 1-minute data. We will update `core/ml_engine.py` with a specific training method for 0DTE models. We will add a training trigger in `backtesting_lab/app.py`. Finally, we will update `live_trading_hub/strategy_engine.py` to load this model and use the standardized features.

**Tech Stack:** Python, pandas, XGBoost, Streamlit.

---

### Task 1: Shared Models Directory and Core Data Normalization

**Files:**
- Create: `core/models/.gitkeep`
- Modify: `core/data.py`
- Modify: `live_trading_hub/data_streamer.py`

- [ ] **Step 1: Create the shared models directory**

```bash
mkdir -p core/models
echo "" > core/models/.gitkeep
```

- [ ] **Step 2: Update `core/data.py` to add `VWAP_Proxy_Dist`**

Open `core/data.py` and modify the `preprocess_data` function (or similar) to ensure `VWAP_Proxy_Dist` is calculated.

```python
    # After calculating VWAP_Proxy:
    if 'VWAP_Proxy' in df.columns:
        df['VWAP_Proxy_Dist'] = (df['Close'] / df['VWAP_Proxy']) - 1.0
```

- [ ] **Step 3: Update `live_trading_hub/data_streamer.py` to add `VWAP_Proxy_Dist`**

Open `live_trading_hub/data_streamer.py` and modify `_compute_indicators` to calculate `VWAP_Proxy_Dist`.

```python
        # After VWAP Proxy
        df['VWAP_Proxy_Dist'] = (df['Close'] / df['VWAP_Proxy']) - 1.0
```

- [ ] **Step 4: Commit changes**

```bash
git add core/models/.gitkeep core/data.py live_trading_hub/data_streamer.py
git commit -m "feat: add shared models dir and standardize VWAP_Proxy_Dist"
```

---

### Task 2: Specialized 0DTE ML Training Path

**Files:**
- Modify: `core/ml_engine.py`

- [ ] **Step 1: Add `train_0dte` method to `MLSignalFilter` in `core/ml_engine.py`**

```python
    def train_0dte(self, data, trades):
        """Specialized training for the 1-minute 0DTE VWAP Breakout model."""
        if len(trades) < 5: 
            return False, f"Insufficient 1m trade data: Found {len(trades)}. Need at least 5 for 0DTE training."

        df_trades = pd.DataFrame(trades)
        df_trades['label'] = (df_trades['PnL'] > 0).astype(int)
        
        # Specific features for the 0DTE live hub
        training_features = ['MACD_Hist_Dist', 'CMF', 'VWAP_Proxy_Dist']
        
        training_data = []
        labels = []
        for _, trade in df_trades.iterrows():
            entry_date = trade['Date In']
            if entry_date in data.index:
                feat_row = data.loc[entry_date][training_features]
                if not feat_row.isnull().any():
                    training_data.append(feat_row.values)
                    labels.append(trade['label'])

        if len(training_data) < 5:
            return False, "Not enough valid feature rows found for 0DTE."

        X = np.array(training_data).astype(float)
        y = np.array(labels)
        
        if len(np.unique(y)) < 2:
            return False, "Need both Winners and Losers to learn 0DTE signals."

        param_dist = {
            'n_estimators': [50, 100],
            'max_depth': [2, 3],
            'learning_rate': [0.05, 0.1]
        }
        
        from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
        tscv = TimeSeriesSplit(n_splits=2)
        random_search = RandomizedSearchCV(
            self.model, param_distributions=param_dist, 
            n_iter=5, cv=tscv, scoring='accuracy', n_jobs=-1, random_state=42
        )
        
        random_search.fit(X, y)
        self.model = random_search.best_estimator_
        self.reliability_score = random_search.best_score_
        self.is_trained = True
        
        # Save model specifically for live trading hub
        import joblib
        import os
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'my_0dte_model.pkl')
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(self.model, model_path)
        
        return True, f"0DTE Model trained with {len(X)} trades and saved to {model_path}."
```

- [ ] **Step 2: Commit changes**

```bash
git add core/ml_engine.py
git commit -m "feat: add train_0dte specialized training method"
```

---

### Task 3: Dashboard Integration for 1m Training

**Files:**
- Modify: `backtesting_lab/app.py`

- [ ] **Step 1: Add "0DTE Live Model Training" button logic in `backtesting_lab/app.py`**

In the sidebar section, near the existing "Retrain AI Model" button, add a specialized button for 0DTE.

```python
# Before the existing Retrain AI Model button:
st.sidebar.markdown("<p style='font-size: 10px; font-weight: 800; color: #4b5563; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-left: 4px;'>0DTE Live Training</p>", unsafe_allow_html=True)

if st.sidebar.button("Train 0DTE Live Model (1m)"):
    with st.spinner("Fetching 1m SPY data (last 7 days)..."):
        try:
            # Fetch 7 days of 1m data
            d_p_1m, d_m_1m, d_v_1m = fetch_spy_data(interval="1m", years=0, period="7d")
            df_1m = preprocess_data(d_p_1m, d_m_1m, d_v_1m)
            
            # Setup engine
            temp_engine_1m = BacktestEngine(df_1m, initial_capital=capital, risk_pc=risk_pc, global_stop_loss=g_sl, global_take_profit=g_tp, trailing_stop=g_ts, max_hold_bars=g_hold)
            
            # Run VWAP Breakout Strategy (Strategy 37)
            trades_1m, _ = temp_engine_1m.run_strategy("Strategy 37")
            
            # Train specialized 0DTE model
            success, msg = st.session_state.ml_filter.train_0dte(df_1m, trades_1m)
            if success:
                st.sidebar.success(msg)
            else:
                st.sidebar.warning(msg)
        except Exception as e:
            st.sidebar.error(f"0DTE Training Error: {e}")
            
st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
```

- [ ] **Step 2: Commit changes**

```bash
git add backtesting_lab/app.py
git commit -m "feat: add 0DTE Live Model Training button to dashboard"
```

---

### Task 4: Standardize Live Trading Hub Engine

**Files:**
- Modify: `live_trading_hub/strategy_engine.py`

- [ ] **Step 1: Update model loading path in `live_trading_hub/main.py`**

In `live_trading_hub/main.py`, update `self.strategy.load_ai_model("my_0dte_model.pkl")` to point to the shared core directory.

```python
        import os
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'models', 'my_0dte_model.pkl')
        self.strategy.load_ai_model(model_path)
```

- [ ] **Step 2: Update feature extraction in `live_trading_hub/strategy_engine.py`**

Modify `evaluate_bar` and `_get_ai_trust` to use the standardized `VWAP_Proxy_Dist`.

```python
    def evaluate_bar(self, df: pd.DataFrame) -> dict:
        # ...
        # Change VWAP Proximity logic slightly to use VWAP_Proxy_Dist
        vwap_proximity = abs(latest['VWAP_Proxy_Dist']) < 0.005
        # ...
```

```python
    def _get_ai_trust(self, df, signal):
        # ...
        feat_vector = df.iloc[-1][['MACD_Hist_Dist', 'CMF', 'VWAP_Proxy_Dist']].values.reshape(1, -1)
        # ...
```

- [ ] **Step 3: Commit changes**

```bash
git add live_trading_hub/main.py live_trading_hub/strategy_engine.py
git commit -m "feat: standardize live trading hub features and load shared model"
```

# 🤖 AI Selective Master: SPY Backtesting Engine

A professional-grade quantitative workstation for SPY (S&P 500 ETF), combining **36 advanced trading strategies** with an **XGBoost-powered Meta-Learner** orchestrator.

![Trading Dashboard Demo](https://raw.githubusercontent.com/username/repo/main/static/dashboard_preview.png) *(Placeholder - see local dashboard for live charts)*

---

## 🚀 Overview

This platform is designed to identify and execute high-confidence trading signals using a **Dual-Model AI Filter**. It doesn't just run strategies; it judges their probability of success based on current market regimes, macro factors, and historical reliability.

### Key Capabilities
- **36 Quantitative Strategies**: Covering trend following, mean reversion, breakout momentum, and macro overlays.
- **AI Meta-Ensemble**: A higher-order brain that evaluates all strategy signals simultaneously to find the "perfect" entry.
- **Selective Master Mode**: A single-position execution engine that resolves signal collisions by picking the highest-trust strategy for the current bar.
- **Dynamic Regime Detection**: Automatically switches logic based on volatility and trend strength.

---

## 🧠 Core Logics & Architecture

### 1. Dual-Model AI Filter (`ml_engine.py`)
To prevent the "Shape Mismatch" issues common in multi-strategy systems, the engine uses two distinct AI architectures:
- **Base AI**: Dedicated to judging individual strategies using 16 core market indicators (SMA distances, RSI, Volatility, Sentiment).
- **Ensemble Brain**: A 52-dimensional model that evaluates all 36 strategies plus market data to find hidden alpha in signal overlaps.

### 2. Selective Master Orchestrator (`strategies.py`)
When multiple strategies fire at once (e.g., Strategy 12 and Strategy 22 both say BUY), the Master Orchestrator:
1. Calculates a **Trust Score** for each active strategy based on historical performance.
2. Cross-references the **Ensemble Reliability**.
3. Squelches lower-confidence signals to ensure only **ONE** high-probability position is held at a time.

### 3. Alpha Sources
- **Macro Logic**: Integrates Fed Funds Rates and Bond Yield (10Y2Y) spreads.
- **Insider Sentiment**: Scrapes real-time aggregate insider buying activity (via OpenInsider).
- **Price Action**: Deep-dive technicals including Keltner Channels, Ichimoku Clouds, and Volume Profiles.

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+
- [YFinance](https://github.com/ranaroussi/yfinance) for market data.
- [XGBoost](https://xgboost.readthedocs.io/) for AI models.

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/spy-trading-system.git
cd spy-trading-system

# Install dependencies
pip install streamlit pandas numpy yfinance xgboost plotly scikit-learn requests
```

### Running the Dashboard
```bash
streamlit run app.py
```

---

## 📖 How to Use

1. **Retrain the Brain**: 
   - On first launch, select a strategy and click **"Retrain AI Model"** in the sidebar. This builds your local AI probability map.
2. **Execute Backtest**: 
   - Set your date range and global safeguards (Stop Loss, Take Profit).
   - Click **Run Backtest** to see the vectorized execution on the TradingView-style chart.
3. **Analyze Master Mode**:
   - Use the "AI Selective Master" mode to see the **Collision Squelch** metrics — showing exactly which signals were filtered out by the AI to preserve capital.

---

## ⚠️ Known Issues & Caveats

- **Data Density**: The AI Meta-Ensemble requires at least 25-30 historical trades to become reliable. If your selected timeframe is too short, you may see "Insufficient Data" warnings.
- **Sentiment Timeouts**: The OpenInsider API can occasionally time out. The engine implements a silent fallback to 1.0 (neutral) to keep the app responsive.
- **Overfitting**: Ensure you use separate training/testing periods to validate that the AI isn't just memorizing past price action.

---

## 🛤️ Future Roadmap

- [ ] **Genetic Optimization**: Auto-tune strategy parameters (SMA periods, RSI levels) using genetic algorithms.
- [ ] **Options Greeks Overlay**: Factor in IV Crush and Delta/Gamma risk for SPY option pairings.
- [ ] **Live Execution**: Integration with IBKR (Interactive Brokers) via TWS API for real-time automated trading.
- [ ] **Deep Sentiment**: NLP analysis of Fed meeting minutes and earnings transcripts.

---

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for new strategies or ML improvements.

*Disclaimer: This is research software. Past performance does not guarantee future results. Trade at your own risk.*

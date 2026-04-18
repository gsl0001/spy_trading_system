# 🤖 QuantOS: AI Selective Master System

A professional-grade quantitative ecosystem for SPY (S&P 500 ETF), split into two specialized platforms sharing a common high-performance core.

---

## 🏗️ Project Architecture

The system is restructured into three primary layers for maximum modularity and scalability:

1.  **`core/`**: Shared quantitative logic, including 37+ trading strategies, the XGBoost Meta-Learner, and macro/sentiment engines.
2.  **`backtesting_lab/`**: An advanced research workstation with a modern React frontend and FastAPI backend for deep strategy analysis.
3.  **`live_trading_hub/`**: A production-ready deployment system designed for real-time 0DTE execution and live AI model management.

---

## 🚀 Key Capabilities

- **37 Quantitative Strategies**: Covering trend following, mean reversion, breakout momentum, and volatility compression.
- **AI Meta-Ensemble**: An XGBoost-powered brain that evaluates all strategy signals to find hidden alpha.
- **Selective Master Mode**: A single-position orchestrator that resolves signal collisions by picking the highest-trust strategy.
- **Options Greeks Engine**: Synthetic options backtesting with delta-hedging and Greek risk overlays.

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+
- [YFinance](https://github.com/ranaroussi/yfinance) for market data.
- [XGBoost](https://xgboost.readthedocs.io/) for AI models.
- [IB-Insync](https://github.com/erdewit/ib_insync) (for Live Trading Hub).

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/spy-trading-system.git
cd spy-trading-system

# Install dependencies
pip install streamlit pandas numpy yfinance xgboost plotly scikit-learn requests ib_insync fastapi uvicorn loguru
```

---

## 📖 How to Run

The project features specialized entry points in the `scripts/` directory:

### 1. Backtesting Lab (Research Workstation)
Launch the interactive Streamlit dashboard for strategy research and backtesting.
```bash
python scripts/backtest_lab.py
```

### 2. Live Trading Hub (Production Deployment)
Initialize the live trading environment and deploy trained AI models.
```bash
python scripts/live_hub.py
```

---

## 🧠 Core Intelligence

### Dual-Model AI Filter (`core/ml_engine.py`)
The system uses two distinct AI architectures to maintain structural integrity:
- **Base AI**: Judges individual strategy reliability using 16 core market indicators.
- **Ensemble Brain**: A 52-dimensional model evaluating signal overlaps across all 37 strategies.

### Selective Master Orchestrator (`core/strategies.py`)
Picks the single highest-probability trade during signal collisions based on real-time AI Trust Scores.

---

## 🛤️ Roadmap & Future Work
- [ ] **Genetic Optimization**: Auto-tune strategy parameters via GA.
- [ ] **Deep Sentiment**: NLP analysis of Fed minutes and earnings transcripts.
- [ ] **Multi-Asset Support**: Extending the Meta-Learner to QQQ and IWM.

---

## ⚠️ Disclaimer
*This is research software. Past performance does not guarantee future results. Trade at your own risk.*

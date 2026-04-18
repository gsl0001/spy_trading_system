# SPY 0-DTE Autonomous Trading Engine

A professional-grade, event-driven algorithmic trading engine designed for trading **SPY 0-DTE (Zero Days to Expiration)** options via Interactive Brokers (IBKR). The system incorporates real-time streaming data, dynamic technical indicator computation, and machine learning elements to autonomously execute multi-leg option credit spreads.

This repository serves as a localized, terminal-driven trading worker designed to exist as a component of the broader SPY QuantOS Trading System. It is focused on low-latency data processing and immediate order execution.

## 🏗️ Core Architecture

The bot utilizes asynchronous event-handling (`asyncio`) communicating via socket directly with the IBKR API (`ib_insync`). There are four main components handling the trade life cycle:

### 1. Application Orchestrator (`main.py`)
This is the central entry point. It manages the asynchronous event loop, instantiates subsystems, and processes data pipeline triggers.
- Automatically connects to TWS or IB Gateway on user-defined ports.
- Routes newly generated 1-minute market bars to strategy logic asynchronously without blocking incoming data feeds.

### 2. Live Data Streamer (`data_streamer.py`)
Responsible for fetching options and underlying data for SPY. 
- Conducts an initial sync to download recent historical 1-minute bars to bootstrap the calculation matrix.
- Updates an internal Pandas DataFrame memory state continuously upon the close of each `1 min` bar.
- Computes highly optimized vectorized Pandas technical indicators:
  - VWAP Proxy (Volume-weighted Typical Price)
  - Bollinger Bands (20, 2)
  - Keltner Channels (20, 1.5)
  - Expected Move / ATR 14
  - MACD and Chaikin Money Flow (Institutional Volume proxy).

### 3. Strategy & ML Engine (`strategy_engine.py`)
Contains the algorithmic conditions targeting the **VWAP Keltner Compression Breakout Strategy**.
- Assesses proximity to volume pivots (VWAP).
- Identifies explosive volume releases inside Keltner/Bollinger squeezes.
- Uses Chaikin Money Flow and MACD momentum thresholds.
- **AI Integration Verification:** Seamlessly loads a local Random Forest/XGBoost Pickle model (`my_0dte_model.pkl`) and passes a dynamic feature vector subset to output trading confidence limits before clearing a trigger.

### 4. Autonomous Execution (`execution_engine.py`)
Prices and fires live orders dynamically into the options market without human interaction.
- Locates today's exact 0-DTE options expiration chain.
- Pinpoints At-The-Money (ATM) anchor strikes based on the live SPY proxy price at signal generation.
- Generates `BAG` underlying complex order contracts.
- **LONG Triggers** construct *Bull Put Credit Spreads*.
- **SHORT Triggers** construct *Bear Call Credit Spreads*.
- Validates the current bid-ask mid-price locally to ensure safety conditions before simulated or actual limits execute.

---

## 📋 Prerequisites

To run this live local system alongside the overall FastAPI system, ensure:
1. **Python 3.10+** (Python 3.12+ recommended/tested).
2. **Interactive Brokers TWS or IB Gateway** is installed and actively running on your desktop.
3. Your trading account has the live data permissions for `US Equities` and `OPRA` options feeds to receive un-delayed tape.

## 🚀 Setup & Installation

1. **Install Dependencies** using UV or Pip.
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This relies on `ib_insync`, `pandas`, `numpy`, `scikit-learn` or `joblib` for ML models.*

2. **Configure Interactive Brokers** for socket integration:
   - Launch your *IB Gateway* or *TWS* client.
   - Navigate to **File -> Global Configuration -> API -> Settings**.
   - Check **"Enable ActiveX and Socket Clients"**.
   - Note your configured **Socket Port**:
     - `7497` is configured by default for Paper Trading.
     - `7496` is assigned normally for Live accounts.
   - For execution testing, uncheck "Read-Only API".

## 💻 Running the Bot

Run the centralized bootstrapper with:
```bash
python main.py
```
*(Optionally use `uv run main.py` if using UV virtual environments).*

### Expected Boot Sequence:
1. **Model Loading:** The system attempts to load `my_0dte_model.pkl`. If not found, it runs fallback dummy logic.
2. **IBKR Sync:** The bot establishes an API connection over the assigned loop port `7497`. A graceful failure message is printed if TWS isn't open.
3. **Data Initialization:** Historical bars for SPY stream in to calculate real-time technical anchors.
4. **Active Surveillance:** The system outputs live market ticker summaries per 1-minute close.
5. **Execution Firing:** When market flow generates an anomaly matching the Keltner parameters combined with > 60% machine learning confidence, a simulated execution protocol begins.

> **Execution Safety Note:** The `self.ib.placeOrder(contract, order)` line inside `execution_engine.py` is safely commented out by default, to ensure no unintended execution occurs during strategy testing or code review phases.

---

### Integration with Next-Gen Server Environment

This `live_0dte_system` operates natively as a subsystem/terminal. The parent directory features a robust asynchronous `FastAPI` instance serving endpoints across:
- Advanced configuration management (`config_manager`).
- Detailed local SQlite Reporting ledgers & Machine learning ensemble pipelines (`ml_engine.py`).
- WebSocket multi-client GUI distribution.

To attach this terminal bot structure to your advanced Dashboard, you can execute the server root system by executing:
```bash
python run_server.py
```
It will route endpoints up through `http://0.0.0.0:8000`.

---
**⚠️ Risk Disclaimer:** The logic contained herein targets highly volatile intraday derivatives. Algorithmic software logic executes strictly and blindly. This system is created for research and educational purposes. ALWAYS validate the execution environment with simulated or paper-trading accounts prior to deployment into live portfolios.

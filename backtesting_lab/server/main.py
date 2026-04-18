"""
FastAPI Application — Main entry point for the SPY Trading System API.
"""
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
from loguru import logger

from backtesting_lab.config.config_manager import load_config, get_config
from core.ml_engine import MLEnsembleFilter
from backtesting_lab.server.services.trade_journal import TradeJournal
from backtesting_lab.server.services.notification_service import NotificationService
from backtesting_lab.server.services.report_generator import ReportGenerator
from backtesting_lab.server.services.trading_orchestrator import TradingOrchestrator
from backtesting_lab.server.routers.ws import ws_manager

# ──────────────────────────────────────────────
# Global Service Instances
# ──────────────────────────────────────────────
ml_filter = MLEnsembleFilter()
journal = None
notifier = None
report_gen = None
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown events."""
    global journal, notifier, report_gen, orchestrator

    # Load configuration
    config = load_config()
    logger.info(f"QuantOS v{config.system.version} starting...")
    logger.info(f"Mode: {config.system.mode} | Dry Run: {config.system.dry_run}")

    # Configure logging
    logger.add(
        "data/logs/quantos_{time}.log",
        rotation="10 MB",
        retention="30 days",
        level=config.system.log_level,
    )

    # Initialize services
    ml_filter.confidence_threshold = config.ml.confidence_threshold
    journal = TradeJournal(config.reporting.trade_journal_path)
    notifier = NotificationService(config.notifications.model_dump())
    report_gen = ReportGenerator(journal, config.reporting.reports_output_path)
    orchestrator = TradingOrchestrator(config, ml_filter, journal, notifier)

    # Inject dependencies into routers
    from backtesting_lab.server.routers import ml as ml_router
    from backtesting_lab.server.routers import live as live_router
    from backtesting_lab.server.routers import reports as reports_router

    ml_router.set_ml_filter(ml_filter)
    live_router.set_orchestrator(orchestrator)
    reports_router.set_services(journal, report_gen)

    logger.info("All services initialized. Server ready.")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if orchestrator and orchestrator._is_running:
        orchestrator.stop()
    logger.info("Shutdown complete.")


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title="SPY QuantOS Trading System",
    description="Production-grade autonomous SPY trading platform with 37 strategies and AI ensemble filtering.",
    version="5.0.0",
    lifespan=lifespan,
)

# CORS — Allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Register Routers
# ──────────────────────────────────────────────
from backtesting_lab.server.routers.backtest import router as backtest_router
from backtesting_lab.server.routers.config import router as config_router
from backtesting_lab.server.routers.ml import router as ml_router
from backtesting_lab.server.routers.live import router as live_router
from backtesting_lab.server.routers.reports import router as reports_router
from backtesting_lab.server.routers.deployment import router as deployment_router

app.include_router(backtest_router)
app.include_router(config_router)
app.include_router(ml_router)
app.include_router(live_router)
app.include_router(reports_router)
app.include_router(deployment_router)


# ──────────────────────────────────────────────
# WebSocket Endpoint
# ──────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client (keepalive/commands)
            data = await websocket.receive_text()
            # Echo back as acknowledgment
            await ws_manager.send_personal(websocket, {
                "type": "ack",
                "data": {"received": data}
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ──────────────────────────────────────────────
# Health & Info Endpoints
# ──────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """System health check."""
    config = get_config()
    return {
        "status": "ok",
        "version": config.system.version,
        "mode": config.system.mode,
        "dry_run": config.system.dry_run,
        "ml_trained": ml_filter.is_trained if ml_filter else False,
        "journal_trades": journal.total_trades if journal else 0,
        "ws_clients": ws_manager.client_count,
        "orchestrator_running": orchestrator._is_running if orchestrator else False,
    }


@app.get("/api/market-data/latest")
async def get_latest_market_data():
    """Get the latest SPY price and indicator snapshot."""
    try:
        from core.data import fetch_spy_data, preprocess_data
        d_p, d_m, d_v = fetch_spy_data(interval="1d", years=1)
        df = preprocess_data(d_p, d_m, d_v)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        change = float(latest['Close'] - prev['Close'])
        change_pct = float((latest['Close'] / prev['Close'] - 1) * 100)

        return {
            "symbol": "SPY",
            "price": round(float(latest['Close']), 2),
            "open": round(float(latest['Open']), 2),
            "high": round(float(latest['High']), 2),
            "low": round(float(latest['Low']), 2),
            "volume": int(latest['Volume']),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "sma_20": round(float(latest['SMA_20']), 2) if not pd.isna(latest['SMA_20']) else None,
            "sma_50": round(float(latest['SMA_50']), 2) if not pd.isna(latest['SMA_50']) else None,
            "rsi": round(float(latest['RSI']), 1) if not pd.isna(latest['RSI']) else None,
            "vix": round(float(latest.get('VIX_Close', 0)), 2),
            "timestamp": str(df.index[-1]),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/market-data/sparkline")
async def get_spy_sparkline():
    """Get the last 30 minutes of 1m price data for SPY sparkline."""
    try:
        from core.data import fetch_spy_data
        d_p, _, _ = fetch_spy_data(interval="1m", years=0) # fetch_spy_data with years=0 likely fetches most recent
        if d_p.empty:
            return {"data": []}
        
        last_30 = d_p.tail(30)['Close'].tolist()
        return {"data": [round(x, 2) for x in last_30]}
    except Exception as e:
        return {"error": str(e)}


from fastapi.responses import RedirectResponse

# ──────────────────────────────────────────────
# Static Files (Production Frontend)
# ──────────────────────────────────────────────
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/ui", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

@app.get("/")
async def root_redirect():
    """Redirect root to UI."""
    return RedirectResponse(url="/ui")


# ──────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import pandas as pd  # Needed for market data endpoint

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[PROJECT_ROOT],
        log_level="info",
    )

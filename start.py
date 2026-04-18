"""
QuantOS Trading System - Unified Launcher
Run this script to start the FastAPI backend, the Live Trading Bot, and automatically open the UI.
"""

import sys
import os
import subprocess
import threading
import time
import webbrowser
import logging

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

def run_server():
    """Runs the FastAPI server."""
    print("[SYSTEM] Starting QuantOS Server on http://127.0.0.1:8000 ...")
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )

def run_ibkr_bot():
    """Runs the IBKR live trading bot."""
    bot_path = os.path.join(PROJECT_ROOT, "live_0dte_system", "main.py")
    if os.path.exists(bot_path):
        print(f"[SYSTEM] Starting IBKR Live Trading Bot from {bot_path} ...")
        # Run bot in a subprocess so its output interleaves in the main console
        try:
            subprocess.run([sys.executable, bot_path], cwd=os.path.join(PROJECT_ROOT, "live_0dte_system"))
        except KeyboardInterrupt:
            pass
    else:
        print("[WARNING] IBKR bot script not found.")

def open_ui():
    """Waits for the server to spin up and opens the browser."""
    # Wait a few seconds to ensure the server is ready to accept connections
    time.sleep(3)
    target_url = "http://127.0.0.1:8000/ui"
    print(f"[SYSTEM] Opening UI in default browser: {target_url}")
    webbrowser.open(target_url)

if __name__ == "__main__":
    print("=====================================================")
    print("             SPY QUANT OS INITIALIZING               ")
    print("=====================================================")
    
    # Thread 1: Start UI Browser
    ui_thread = threading.Thread(target=open_ui, daemon=True)
    ui_thread.start()

    # Thread 2: Start Backend Server
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Main Thread: Run IBKR Bot
    # (By running this in the main thread, Ctrl+C will easily kill it)
    try:
        # Give server a tiny headstart
        time.sleep(1)
        run_ibkr_bot()
        
        # If the bot exits (e.g. no IBKR connection), keep server alive if needed
        print("[SYSTEM] Trading Bot process ended. Server is still running.")
        print("[SYSTEM] Press Ctrl+C to stop the entire system.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down QuantOS Unified Launcher...")
        sys.exit(0)

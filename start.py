"""
QuantOS Trading System - Unified Launcher
-----------------------------------------
1. Backtest Lab (Streamlit Research Workstation)
2. Live Trading Hub (0DTE IBKR Deployment)
"""

import sys
import os
import subprocess
import webbrowser
import time
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(PROJECT_ROOT)

def open_browser(url, delay=2):
    """Open the browser after a short delay."""
    time.sleep(delay)
    print(f"[SYSTEM] Opening UI at {url}...")
    webbrowser.open(url)

def run_backtest_lab():
    """Launch the Streamlit research workstation."""
    print("\n[SYSTEM] Launching Backtest Lab...")
    script_path = os.path.join(PROJECT_ROOT, "scripts", "backtest_lab.py")
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser, args=("http://localhost:8501",), daemon=True).start()
    
    subprocess.run([sys.executable, script_path])

def run_live_trading_hub():
    """Launch the Unified Live Trading Server & UI."""
    print("\n[SYSTEM] Launching Live Trading Hub (FastAPI + React)...")
    
    # We use the backtesting_lab/server/main.py as the unified server
    # Or we can run it via uvicorn directly
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser, args=("http://localhost:8000/ui", 3), daemon=True).start()
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "backtesting_lab.server.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("             QUANT OS UNIFIED CONTROLLER             ")
    print("="*50)
    print(" [1] Launch Backtest Lab (Research & Retraining)")
    print(" [2] Launch Live Trading Hub (Unified UI & Bot)")
    print(" [Q] Exit")
    print("-" * 50)
    
    choice = input("\nSelect system to start (1/2/Q): ").strip().upper()
    
    if choice == '1':
        run_backtest_lab()
    elif choice == '2':
        run_live_trading_hub()
    elif choice == 'Q':
        print("\nExiting QuantOS Controller.")
        sys.exit(0)
    else:
        print("\n[ERROR] Invalid choice. Please restart and select 1, 2, or Q.")

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from live_trading_hub.main import IBKRBot

if __name__ == "__main__":
    print("Starting Live Trading Hub...")
    bot = IBKRBot()
    # bot.start() # Assuming there is a start method or similar entry point in IBKRBot

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    import streamlit.web.cli as stcli
    sys.argv = [
        "streamlit",
        "run",
        os.path.join(PROJECT_ROOT, "backtesting_lab", "app.py"),
        "--server.port=8501"
    ]
    sys.exit(stcli.main())

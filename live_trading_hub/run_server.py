"""
QuantOS Server Launcher — Run from the project root to start the FastAPI backend.
"""
import sys
import os

# Set project root to parent directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[PROJECT_ROOT],
        log_level="info",
    )

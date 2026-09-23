import sys
from pathlib import Path

# Add the backend directory to Python's import path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Import the existing FastAPI application
from main import app

# Serve the React/Vite frontend
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app.frontend(
    "/",
    directory=FRONTEND_DIST,
    fallback="index.html",
    check_dir=False,
)
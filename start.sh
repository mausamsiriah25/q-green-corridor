#!/usr/bin/env bash
# Q-GREEN CORRIDOR — one-command startup for Linux/macOS
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=============================================="
echo " Q-GREEN CORRIDOR — starting local prototype"
echo "=============================================="

# ---- backend ----
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "[backend] creating virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi
source "$BACKEND_DIR/.venv/bin/activate"

echo "[backend] installing Python dependencies..."
pip install -q -r "$ROOT_DIR/requirements.txt"

if [ ! -f "$BACKEND_DIR/data/city_network.json" ]; then
  echo "[backend] generating simulated city network..."
  (cd "$BACKEND_DIR/data" && python3 generate_city.py)
fi

echo "[backend] starting FastAPI server on http://localhost:8000 ..."
(cd "$BACKEND_DIR" && uvicorn main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# ---- frontend ----
echo "[frontend] installing npm dependencies (first run only)..."
(cd "$FRONTEND_DIR" && npm install --silent)

echo "[frontend] starting Vite dev server on http://localhost:5173 ..."
(cd "$FRONTEND_DIR" && npm run dev -- --host) &
FRONTEND_PID=$!

echo ""
echo "=============================================="
echo " Backend:  http://localhost:8000/docs"
echo " Frontend: http://localhost:5173"
echo "=============================================="
echo " Press Ctrl+C to stop both servers."
echo ""

trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait

#!/usr/bin/env bash
# Start Briefly AI — FastAPI backend + Vite React frontend
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  Briefly AI v2.0  — FastAPI + React"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

# Check .env exists
if [ ! -f "$ROOT/.env" ]; then
  echo "  ERROR: .env file not found. Copy .env.example and fill in your keys."
  exit 1
fi

# Start backend
(
  cd "$ROOT"
  echo "Starting FastAPI backend..."
  python -m uvicorn backend.main:app --reload --port 8000
) &
BACKEND_PID=$!

# Start frontend
(
  cd "$ROOT/frontend"
  echo "Starting Vite frontend..."
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# Wait for either process to exit, then kill both
wait $BACKEND_PID $FRONTEND_PID

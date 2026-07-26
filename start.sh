#!/bin/bash
# EcoPulse System Startup Script

# 1. Kill any existing processes on our ports
echo "Checking for existing processes on ports 8765 (WebSocket) and 5173 (Frontend)..."
fuser -k 8765/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null
sleep 1

# 2. Start the Backend (in background)
echo "Starting Backend (Simulator + Agent Loop + WebSocket Server)..."
cd backend || exit 1
uv run python -m src.main &
BACKEND_PID=$!
cd ..

# Wait a moment for the backend to initialize
sleep 2

# 3. Start the Frontend
echo "Starting Frontend UI..."
cd frontend || exit 1
npm run dev &
FRONTEND_PID=$!

echo "================================================================"
echo "EcoPulse System is LIVE!"
echo "Backend Agent: Running in background (PID: $BACKEND_PID)"
echo "Frontend UI: http://localhost:5173"
echo "================================================================"
echo "Press Ctrl+C to stop both services."

# Trap Ctrl+C to kill both background processes
trap "echo 'Shutting down EcoPulse...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

# Wait indefinitely so the script doesn't exit
wait

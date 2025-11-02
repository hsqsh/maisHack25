#!/bin/bash

# Activate Python virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "Python virtual environment not found. Please set it up first."
  exit 1
fi

# Start backend server
python3 models/infer_server.py &
BACKEND_PID=$!

# Navigate to frontend directory
cd objectDetectorFE || exit

# Install Node.js dependencies if not already installed
if [ ! -d "node_modules" ]; then
  echo "Installing Node.js dependencies..."
  npm install
fi

# Start frontend server
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
sleep 5

# Open the frontend in the default web browser
if command -v xdg-open > /dev/null; then
  xdg-open http://localhost:5173
elif command -v open > /dev/null; then
  open http://localhost:5173
else
  echo "Please open http://localhost:5173 in your browser."
fi

# Wait for user to terminate the script
echo "Press [CTRL+C] to stop the servers."
wait $BACKEND_PID $FRONTEND_PID
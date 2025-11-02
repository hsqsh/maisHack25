@echo off

REM Activate Python virtual environment
if exist .\.venv\Scripts\activate (
    call .\.venv\Scripts\activate
) else (
    echo Python virtual environment not found. Please set it up first.
    exit /b 1
)

REM Start backend server
start cmd /k "python models\infer_server.py"

REM Navigate to frontend directory
cd objectDetectorFE

REM Install Node.js dependencies if not already installed
if not exist node_modules (
    echo Installing Node.js dependencies...
    npm install
)

REM Start frontend server
start cmd /k "npm run dev"

REM Navigate back to project root
cd ..

REM Open the frontend in the default web browser
start http://localhost:5173

REM Add a delay to ensure backend starts before opening the browser
timeout /t 5 > nul

REM Check if backend is running
curl -s http://localhost:8000/health > nul
if %errorlevel% neq 0 (
    echo Backend failed to start. Please check logs.
    exit /b 1
)

echo Project is running. Backend: http://localhost:8000, Frontend: http://localhost:5173
pause
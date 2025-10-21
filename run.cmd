@echo off
echo Starting Document Processing System...

:: Start Frontend in a new terminal
start cmd /k "cd frontend && echo Starting Frontend... && (if not exist node_modules (echo Installing frontend dependencies... && npm install && echo Frontend dependencies installed.) else (echo Frontend dependencies already installed.)) && npm run dev"

:: Start Backend in a new terminal with separate commands for better error handling
start cmd /k "cd backend && echo Starting Backend... && (if not exist venv (echo Creating virtual environment... && python -m venv venv && echo Virtual environment created.) else (echo Virtual environment already exists.)) && call venv\Scripts\activate.bat && (if not exist venv\Lib\site-packages\flask (echo Installing backend dependencies... && pip install -r requirements.txt) else (echo Backend dependencies already installed)) && python app.py"

echo Both services are starting in separate terminals.
#!/bin/bash

echo "Starting Document Processing System..."

# Start Frontend in a new terminal
(
    cd frontend || exit
    echo "Starting Frontend..."
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
        echo "Frontend dependencies installed."
    else
        echo "Frontend dependencies already installed."
    fi
    npm run dev
) &

# Start Backend in a new terminal with separate commands for better error handling
(
    cd backend || exit
    echo "Starting Backend..."
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "Virtual environment created."
    else
        echo "Virtual environment already exists."
    fi
    source venv/bin/activate
    if ! python3 -c "import flask" 2>/dev/null; then
        echo "Installing backend dependencies..."
        pip install -r requirements.txt
    else
        echo "Backend dependencies already installed."
    fi
    python3 app.py
) &

echo "Both services are starting in separate terminals."

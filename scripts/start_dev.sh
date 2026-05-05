#!/bin/bash
# Linux/Mac startup script - Development environment (background mode)

echo "========================================"
echo "  Starting Development Environment"
echo "========================================"

# Change to project root directory
cd "$(dirname "$0")/.." || exit

# Check and create virtual environment if not exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "Virtual environment not found, creating..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Please ensure Python 3 is installed and accessible"
        exit 1
    fi
    echo "Virtual environment created successfully"
fi

# Activate virtual environment
source .venv/bin/activate
echo "Virtual environment activated"

# Upgrade pip and install dependencies
echo "Checking dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi
echo "Dependencies installed successfully"

# Set environment variable
export ENVIRONMENT=development

# Create logs directory if not exists
mkdir -p logs

# Start application in background
nohup python start.py > logs/app_dev.log 2>&1 &
APP_PID=$!

echo $APP_PID > scripts/app_dev.pid
echo ""
echo "Application started in background (PID: $APP_PID)"
echo "To view logs: tail -f logs/app_dev.log"
echo "To stop the application, run: bash scripts/stop.sh"
echo "========================================"

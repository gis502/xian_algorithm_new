#!/bin/bash
# Linux/Mac stop script - Stop the application

echo "========================================"
echo "  Stopping Application"
echo "========================================"

# Change to project root directory
cd "$(dirname "$0")/.." || exit

# Function to stop a process by PID file
stop_process() {
    local pid_file=$1
    local env_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $env_name (PID: $pid)..."
            kill "$pid"
            
            # Wait for process to stop
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "Force stopping $env_name..."
                kill -9 "$pid"
            fi
            
            rm -f "$pid_file"
            echo "$env_name stopped"
        else
            echo "$env_name not running (stale PID file removed)"
            rm -f "$pid_file"
        fi
    else
        echo "No $env_name PID file found"
    fi
}

# Stop development environment
stop_process "scripts/app_dev.pid" "Development environment"

# Stop production environment
stop_process "scripts/app_prod.pid" "Production environment"

# Also try to find any remaining python processes running start.py
REMAINING_PIDS=$(ps aux | grep "[p]ython.*start.py" | awk '{print $2}')
if [ -n "$REMAINING_PIDS" ]; then
    echo "Found additional Python processes, stopping..."
    echo "$REMAINING_PIDS" | xargs kill 2>/dev/null
    sleep 2
    
    # Force kill if still running
    REMAINING_PIDS=$(ps aux | grep "[p]ython.*start.py" | awk '{print $2}')
    if [ -n "$REMAINING_PIDS" ]; then
        echo "$REMAINING_PIDS" | xargs kill -9 2>/dev/null
    fi
fi

echo "========================================"
echo "All applications stopped"

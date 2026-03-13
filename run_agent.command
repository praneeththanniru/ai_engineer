#!/bin/bash
# ============================================
# Antigravity Agent Launcher for macOS — Double-Click Ready
# ============================================

# Exit on error
set -e

# Get the directory where this script lives (project root)
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to project root
cd "$PROJECT_DIR"

# Activate virtual environment
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo "❌ Virtual environment not found in $PROJECT_DIR/venv"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Run the agent
echo "🚀 Starting Antigravity Agent..."
python3 -m src.agent

# Keep the Terminal open after exit
echo "✅ Agent finished. Press any key to close this Terminal."
read -n 1 -
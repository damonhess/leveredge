#!/bin/bash
# Serve script for LeverEdge Documentation Site
# Usage: ./serve.sh [port]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=${1:-8080}

echo "=========================================="
echo "  LeverEdge Documentation Server"
echo "=========================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if not installed
if ! python -c "import mkdocs" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Create assets directory if it doesn't exist
if [ ! -d "docs/assets" ]; then
    mkdir -p docs/assets
fi

# Create placeholder logo if it doesn't exist
if [ ! -f "docs/assets/logo.png" ]; then
    echo "Note: docs/assets/logo.png not found. Using placeholder."
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > docs/assets/logo.png 2>/dev/null || true
fi

echo ""
echo "Starting development server..."
echo "Documentation will be available at: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""

# Serve with live reload
mkdocs serve --dev-addr="0.0.0.0:$PORT"

#!/bin/bash
# Build script for LeverEdge Documentation Site
# Usage: ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  LeverEdge Documentation Build Script"
echo "=========================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not installed."
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

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create assets directory if it doesn't exist
if [ ! -d "docs/assets" ]; then
    mkdir -p docs/assets
fi

# Create placeholder logo if it doesn't exist
if [ ! -f "docs/assets/logo.png" ]; then
    echo "Note: docs/assets/logo.png not found. Using placeholder."
    # Create a simple placeholder (1x1 transparent PNG)
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > docs/assets/logo.png 2>/dev/null || true
fi

# Build the documentation
echo "Building documentation..."
mkdocs build --strict

echo ""
echo "=========================================="
echo "  Build Complete!"
echo "=========================================="
echo ""
echo "Output directory: $SCRIPT_DIR/site/"
echo ""
echo "To serve locally, run: ./serve.sh"
echo "To deploy, copy the 'site/' directory to your web server."
echo ""

# Deactivate virtual environment
deactivate

#!/bin/bash

# Bankruptcy Query Optimizer - Quick Start Script

# Ensure we run from repo root
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "======================================"
echo "Bankruptcy Query Optimizer Quick Start"
echo "======================================"
echo

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY is not set"
    echo "Please run: export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

echo
echo "======================================"
echo "Running test query..."
echo "======================================"
python3 optimize_query.py "preference action trustee motion"

echo
echo "======================================"
echo "Setup complete! You can now use:"
echo "  python3 optimize_query.py 'your query'"
echo "  python3 optimize_query.py --json 'Till v. SCS Credit'"
echo "  bash scripts/build_lambda_package.sh"
echo "  bash scripts/deploy.sh --stage dev"
echo "======================================"

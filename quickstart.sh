#!/bin/bash

# Bankruptcy Query Optimizer - Quick Start Script

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
pip3 install openai-agents pydantic

echo
echo "Running setup check..."
python3 check_setup.py

echo
echo "======================================"
echo "Running test query..."
echo "======================================"
python3 optimize_query.py "preference action trustee motion"

echo
echo "======================================"
echo "Setup complete! You can now use:"
echo "  python3 optimize_query.py 'your query'"
echo "  python3 demo_optimizer.py"
echo "  python3 example_usage.py"
echo "======================================"
#!/bin/bash
# Quick start script for Dialed

# Navigate to project directory
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Run all services
python run_all.py

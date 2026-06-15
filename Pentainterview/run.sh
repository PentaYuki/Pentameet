#!/bin/bash

# Interview Assistant Run Script
# ==============================

# 1. Kill any existing process on port 5005
echo "Cleaning up port 5005..."
lsof -ti tcp:5005 | xargs kill -9 2>/dev/null || true

# 2. Set environment variables to prevent Segfault on macOS
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# 3. Set API Key
export GEMINI_API_KEY="AIzaSyALTVn0UWLqkXQE5MpaHnrzNlr1chjfE-Q"

# 4. Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

# 5. Start Backend
echo "Starting Interview Assistant Backend..."
python3 backend.py

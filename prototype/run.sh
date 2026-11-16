#!/usr/bin/env sh
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
echo "Open http://localhost:8000"
python3 -m uvicorn app.server:app --port 8000

@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
start "" http://localhost:8000
python -m uvicorn app.server:app --port 8000

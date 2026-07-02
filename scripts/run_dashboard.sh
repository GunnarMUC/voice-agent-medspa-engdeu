#!/bin/bash
# Dashboard starten – Web-Oberfläche für Agent-Steuerung

cd "$(dirname "$0")/.."
if [ -d "venv" ]; then
  source venv/bin/activate
fi
exec uvicorn dashboard.api:app --host 0.0.0.0 --port 3000

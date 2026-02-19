#!/bin/bash
# Dashboard starten – Web-Oberfläche für Agent-Steuerung

cd "$(dirname "$0")/.."
for v in venv /Users/ai_dev/voice-agent-medspa/venv; do
  [ -d "$v" ] && source "$v/bin/activate" && break
done
exec uvicorn dashboard.api:app --host 0.0.0.0 --port 3000

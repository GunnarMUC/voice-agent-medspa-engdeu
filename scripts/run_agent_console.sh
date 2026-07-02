#!/bin/bash
# Voice Agent – Lokaler Konsolen-Modus (vollständig offline)
# STT → RAG → LLM → TTS, keine Cloud-APIs nötig

cd "$(dirname "$0")/.."
if [ -d "venv" ]; then
  source venv/bin/activate
fi
exec python -m agent.main console-local

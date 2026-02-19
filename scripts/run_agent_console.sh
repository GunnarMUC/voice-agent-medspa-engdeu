#!/bin/bash
# Voice Agent – Lokaler Konsolen-Modus (vollständig offline)
# STT → RAG → LLM → TTS, keine Cloud-APIs nötig

cd "$(dirname "$0")/.."
for v in venv ../../voice-agent-medspa/venv; do
  [ -d "$v" ] && source "$v/bin/activate" && break
done
exec python -m agent.main console-local

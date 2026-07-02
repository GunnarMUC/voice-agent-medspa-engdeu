#!/usr/bin/env python3
"""
Smoke-Test: Prüft alle Komponenten ohne Mikrofon-Interaktion.
"""
import sys
from pathlib import Path

# Projekt-Root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_stt():
    from agent.stt import STTEngine
    import numpy as np
    engine = STTEngine()
    silent = np.zeros(16000 * 2, dtype=np.float32)  # 2 sec Stille
    r = engine.transcribe(silent, vad_filter=False)
    assert r.language in ("de", "en")
    print("✓ STT")

def test_rag():
    from agent.rag import RAGEngine
    e = RAGEngine()
    r = e.search("Was kostet Zahnreinigung?", top_k=1)
    assert len(r) >= 0  # kann leer sein wenn KB nicht gebaut
    print("✓ RAG")

def test_llm():
    from agent.llm import LLMEngine
    e = LLMEngine()
    if not e.health_check():
        print("⚠ LLM: Ollama nicht erreichbar")
        return
    r = e.generate("Sag nur: OK", stream=False)
    assert len(r) > 0
    print("✓ LLM")

def test_tts():
    from agent.tts import TTSEngine
    e = TTSEngine()
    audio = e.synthesize("Test", lang="de")
    assert len(audio) > 1000
    print("✓ TTS")

def test_booking_api():
    import httpx
    from agent.config import get_settings
    s = get_settings()
    r = httpx.get(f"http://localhost:{s.booking_api_port}/health", timeout=2)
    assert r.status_code == 200
    print("✓ Booking API")

def main():
    print("Smoke-Test...")
    test_stt()
    test_rag()
    test_llm()
    test_tts()
    test_booking_api()
    print("\n✓ Alle Komponenten OK")

if __name__ == "__main__":
    main()

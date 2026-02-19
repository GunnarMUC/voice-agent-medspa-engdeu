"""
Dashboard API – Agent starten/stoppen, Klinik-Daten laden, KB leeren.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.config import get_settings
from agent.rag import RAGEngine
from dashboard.state import load_state, save_state
from scraper.build_kb import chunk_text
from scraper.clean import clean_document

app = FastAPI(title="Voice Agent Dashboard", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Agent-Subprocess
_agent_process = None


class ClinicLoadRequest(BaseModel):
    url: str  # HttpUrl würde strikter prüfen, str erlaubt auch http


class LanguageRequest(BaseModel):
    language: str  # "de" | "en"


@app.get("/api/status")
def get_status():
    """Agent-Status, aktuelle Klinik, Sprache."""
    state = load_state()
    rag = RAGEngine()
    try:
        collection = rag._get_collection()
        chunk_count = collection.count()
    except Exception:
        chunk_count = 0
    return {
        "agent_running": _agent_process is not None and _agent_process.poll() is None,
        "language": state.get("language", "de"),
        "current_clinic_url": state.get("current_clinic_url", ""),
        "chunk_count": chunk_count,
    }


@app.post("/api/agent/start")
def start_agent(lang: str = "de"):
    """Startet den Voice Agent (console-local)."""
    global _agent_process
    if _agent_process is not None and _agent_process.poll() is None:
        return {"status": "already_running", "message": "Agent läuft bereits."}

    state = load_state()
    state["language"] = lang
    save_state(state)

    for candidate in [
        ROOT / "venv" / "bin" / "python",
        Path("/Users/ai_dev/voice-agent-medspa/venv/bin/python"),
        Path(sys.executable),
    ]:
        if Path(candidate).exists():
            venv_python = candidate
            break
    else:
        venv_python = Path(sys.executable)

    env = dict(__import__("os").environ)
    env["AGENT_DEFAULT_LANGUAGE"] = lang
    env["PYTHONPATH"] = str(ROOT)

    _agent_process = subprocess.Popen(
        [str(venv_python), "-m", "agent.main", "console-local"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"status": "started", "pid": _agent_process.pid}


@app.post("/api/agent/stop")
def stop_agent():
    """Stoppt den Voice Agent."""
    global _agent_process
    if _agent_process is None:
        return {"status": "stopped", "message": "Agent war nicht aktiv."}
    if _agent_process.poll() is None:
        _agent_process.terminate()
        _agent_process.wait(timeout=5)
    _agent_process = None
    return {"status": "stopped"}


@app.post("/api/clinic/load")
async def load_clinic(req: ClinicLoadRequest):
    """Crawlt Webseite und baut Wissensbasis auf. Ersetzt bestehende Daten."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL erforderlich")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from scraper.crawl import crawl_url_sync
        markdown = crawl_url_sync(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl fehlgeschlagen: {str(e)}")

    if not markdown or len(markdown.strip()) < 50:
        raise HTTPException(status_code=400, detail="Zu wenig Inhalt von der Webseite extrahiert.")

    rag = RAGEngine()
    cleared = rag.clear()

    chunks = chunk_text(markdown)
    if not chunks:
        raise HTTPException(status_code=400, detail="Keine verwertbaren Text-Chunks gefunden.")

    rag.add_documents(
        chunks,
        metadatas=[{"source": url, "url": url}] * len(chunks),
    )

    state = load_state()
    state["current_clinic_url"] = url
    state["chunk_count"] = len(chunks)
    save_state(state)

    return {
        "status": "loaded",
        "url": url,
        "chunks_added": len(chunks),
        "chunks_cleared": cleared,
    }


@app.post("/api/clinic/clear")
def clear_clinic():
    """Leert die Wissensbasis (für neue Klinik)."""
    rag = RAGEngine()
    cleared = rag.clear()

    state = load_state()
    state["current_clinic_url"] = ""
    state["chunk_count"] = 0
    save_state(state)

    return {"status": "cleared", "chunks_removed": cleared}


@app.put("/api/language")
def set_language(req: LanguageRequest):
    """Setzt die Standard-Sprache (de/en)."""
    lang = req.language.lower()
    if lang not in ("de", "en"):
        raise HTTPException(status_code=400, detail="Sprache muss 'de' oder 'en' sein.")
    state = load_state()
    state["language"] = lang
    save_state(state)
    return {"language": lang}


app.mount("/static", StaticFiles(directory=ROOT / "dashboard" / "static"), name="static")


@app.get("/")
def index():
    """Dashboard HTML."""
    return FileResponse(ROOT / "dashboard" / "static" / "index.html")

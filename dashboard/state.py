"""Persistenter Zustand für Dashboard (Klinik, Sprache)."""
import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "dashboard_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"language": "de", "current_clinic_url": "", "chunk_count": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

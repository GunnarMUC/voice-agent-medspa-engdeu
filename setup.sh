#!/bin/bash
# =============================================================================
# Voice Agent MedSpa – Setup-Skript
# Lädt TTS-Modelle, erstellt virtuelle Umgebung, installiert Abhängigkeiten.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " Voice Agent MedSpa – Setup"
echo "========================================="
echo ""

# 1. Python-Version prüfen
echo "[1/5] Prüfe Python-Version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "  Python $PYTHON_VERSION"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "  [FEHLER] Python 3.10+ wird benötigt."
    exit 1
fi
echo "  ✓ OK"
echo ""

# 2. Virtuelle Umgebung erstellen
echo "[2/5] Erstelle virtuelle Umgebung..."
if [ -d "venv" ]; then
    echo "  venv/ existiert bereits – überspringe."
else
    python3 -m venv venv
    echo "  ✓ venv erstellt."
fi
echo ""

# 3. Abhängigkeiten installieren
echo "[3/5] Installiere Python-Abhängigkeiten..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo "  ✓ Abhängigkeiten installiert."
echo ""

# 4. Ollama-Modelle prüfen
echo "[4/5] Prüfe Ollama-Modelle..."
if command -v ollama &>/dev/null; then
    if ollama list 2>/dev/null | grep -q "llama3.1"; then
        echo "  ✓ llama3.1 gefunden."
    else
        echo "  Lade llama3.1:8b..."
        ollama pull llama3.1:8b
    fi
    if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
        echo "  ✓ nomic-embed-text gefunden."
    else
        echo "  Lade nomic-embed-text..."
        ollama pull nomic-embed-text
    fi
else
    echo "  [WARNUNG] Ollama nicht installiert."
    echo "  Installiere: curl -fsSL https://ollama.ai/install.sh | sh"
fi
echo ""

# 5. TTS-Modelle herunterladen
echo "[5/5] Lade Piper TTS-Modelle..."
mkdir -p tts-models

DE_MODEL="tts-models/de_DE-thorsten-high.onnx"
DE_CONFIG="tts-models/de_DE-thorsten-high.onnx.json"
EN_MODEL="tts-models/en_US-amy-medium.onnx"
EN_CONFIG="tts-models/en_US-amy-medium.onnx.json"

# Basis-URL für Piper-Modelle
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main"

download_if_missing() {
    local url="$1"
    local dest="$2"
    if [ -f "$dest" ]; then
        echo "  ✓ $dest vorhanden."
    else
        echo "  Lade $dest..."
        if command -v wget &>/dev/null; then
            wget -q -O "$dest" "$url"
        elif command -v curl &>/dev/null; then
            curl -sL -o "$dest" "$url"
        else
            echo "  [FEHLER] Weder wget noch curl gefunden."
            exit 1
        fi
        echo "  ✓ $dest heruntergeladen."
    fi
}

download_if_missing "$BASE_URL/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx" "$DE_MODEL"
download_if_missing "$BASE_URL/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json" "$DE_CONFIG"
download_if_missing "$BASE_URL/en/en_US/amy/medium/en_US-amy-medium.onnx" "$EN_MODEL"
download_if_missing "$BASE_URL/en/en_US/amy/medium/en_US-amy-medium.onnx.json" "$EN_CONFIG"

# Piper CLI prüfen
echo ""
if ! command -v piper &>/dev/null; then
    echo "  [WARNUNG] 'piper' CLI nicht im PATH."
    echo "  Installiere: pip install piper-tts"
    echo "  Oder: https://github.com/rhasspy/piper"
fi

echo ""
echo "========================================="
echo " Setup abgeschlossen!"
echo ""
echo " Nächste Schritte:"
echo "  1. Ollama starten:   ollama serve"
echo "  2. .env kopieren:    cp .env.example .env"
echo "  3. Booking-API:      uvicorn booking.api:app --port 8080 &"
echo "  4. Agent starten:    python -m agent.main console-local"
echo "  5. Dashboard:        uvicorn dashboard.api:app --port 3000"
echo "========================================="
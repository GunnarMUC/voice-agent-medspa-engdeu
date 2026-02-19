# Voice Agent MedSpa / Zahnklinik

Ein **sprachgesteuerter KI-Assistent** für Zahnkliniken und Med Spas. Der Agent arbeitet als virtueller Telefonempfang: Er beantwortet Fragen zu Leistungen, Öffnungszeiten und Team, führt Terminbuchungen durch und spricht **Deutsch** sowie **Englisch**.

## Highlights

- **Lokale Ausführung** – Keine Cloud-APIs erforderlich (Ollama, Piper TTS, faster-whisper)
- **GDPR-konform** – Daten bleiben auf Ihrem System, keine externen Dienste
- **Zweisprachig** – Deutsch und Englisch
- **RAG-basiert** – Klinik-spezifisches Wissen aus Webseiten oder Markdown-Dateien
- **Terminbuchung** – Integration mit einer lokalen Booking-API
- **Web-Dashboard** – Einfache Steuerung für Präsentationen (Agent starten/stoppen, Klinik-Daten laden)

## Architektur

```
┌─────────────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│  Mikrofon (STT) │────▶│   RAG    │────▶│   LLM   │────▶│ TTS      │
│  faster-whisper │     │ ChromaDB │     │ Ollama  │     │ Piper    │
└─────────────────┘     └──────────┘     └─────────┘     └──────────┘
                               │                │
                               │                └──▶ Booking API (Termine)
                               │
                               └──▶ Klinik-Webseite (Crawl) oder lokale Markdown-Dateien
```

## Voraussetzungen

- **Python 3.10+**
- **Ollama** – [ollama.ai](https://ollama.ai) installieren und folgende Modelle laden:
  ```bash
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
  ```
- **Piper TTS** – Deutsche und englische Sprachmodelle (siehe [TTS-Modelle](#tts-modelle))
- **Mikrofon und Lautsprecher** für den Konsolen-Modus

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/GunnarMUC/voice-agent-medspa-engdeu.git
cd voice-agent-medspa-engdeu
```

### 2. Virtuelle Umgebung und Abhängigkeiten

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Umgebungsvariablen

Kopieren Sie die Beispiel-Konfiguration und passen Sie sie bei Bedarf an:

```bash
cp .env.example .env
```

Wichtige Einstellungen in `.env`:

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `OLLAMA_BASE_URL` | Ollama-Server | `http://localhost:11434` |
| `OLLAMA_MODEL` | Sprachmodell | `llama3.1:8b` |
| `OLLAMA_EMBED_MODEL` | Embedding-Modell | `nomic-embed-text` |
| `WHISPER_MODEL_SIZE` | STT-Größe (tiny/base/small/medium) | `base` |
| `TTS_DE_MODEL_PATH` | Pfad zum deutschen Piper-Modell | `tts-models/de_DE-thorsten-high.onnx` |
| `TTS_EN_MODEL_PATH` | Pfad zum englischen Piper-Modell | `tts-models/en_US-amy-medium.onnx` |
| `BOOKING_API_PORT` | Port der Booking-API | `8080` |
| `AGENT_DEFAULT_LANGUAGE` | Standardsprache (de/en) | `de` |

### 4. TTS-Modelle

Laden Sie die Piper-Modelle herunter und legen Sie sie im Ordner `tts-models/` ab:

- **Deutsch:** [de_DE-thorsten-high](https://huggingface.co/rhasspy/piper-voices/tree/main/de/de_DE/thorsten/high)
- **Englisch (US):** [en_US-amy-medium](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/amy/medium)

Benötigt werden die `.onnx`- und `.onnx.json`-Dateien. Beispiel:

```
tts-models/
├── de_DE-thorsten-high.onnx
├── de_DE-thorsten-high.onnx.json
├── en_US-amy-medium.onnx
└── en_US-amy-medium.onnx.json
```

## Schnellstart

### Option A: Web-Dashboard (empfohlen für Präsentationen)

1. **Booking-API starten** (in einem Terminal):
   ```bash
   uvicorn booking.api:app --host 0.0.0.0 --port 8080
   ```

2. **Dashboard starten** (in einem weiteren Terminal):
   ```bash
   uvicorn dashboard.api:app --host 0.0.0.0 --port 3000
   ```

3. **Browser öffnen:** [http://localhost:3000](http://localhost:3000)

4. Im Dashboard:
   - **Klinik-URL eingeben** (z.B. `https://beispiel-zahnarzt.de`) und auf „Daten laden“ klicken – die Webseite wird gecrawlt und die Wissensbasis befüllt
   - **Sprache wählen** (Deutsch/English)
   - **Agent starten** – der Agent läuft lokal mit Mikrofon und Lautsprecher

### Option B: Konsolen-Modus (ohne Dashboard)

```bash
# Booking-API im Hintergrund
uvicorn booking.api:app --host 0.0.0.0 --port 8080 &

# Agent starten
python -m agent.main console-local
```

Sprache über Umgebungsvariable:

```bash
AGENT_DEFAULT_LANGUAGE=en python -m agent.main console-local
```

## Projektstruktur

```
voice-agent-medspa-engdeu/
├── agent/                 # Voice-Agent-Kern
│   ├── main.py            # Einstieg (LiveKit + console-local)
│   ├── config.py          # Konfiguration (.env)
│   ├── stt.py             # Speech-to-Text (faster-whisper)
│   ├── tts.py             # Text-to-Speech (Piper)
│   ├── llm.py             # LLM (Ollama)
│   ├── rag.py             # RAG-Engine (ChromaDB)
│   └── prompts.py         # System-Prompts
├── booking/               # Terminbuchungs-API
│   ├── api.py             # FastAPI-Endpoints
│   ├── database.py        # SQLite-Persistenz
│   └── models.py          # Pydantic-Modelle
├── dashboard/             # Web-Dashboard
│   ├── api.py             # FastAPI (Agent-Steuerung, Klinik-Daten)
│   ├── state.py           # Persistenz (Sprache, Klinik-URL)
│   └── static/            # Frontend (HTML/CSS/JS)
├── scraper/               # Web-Crawler & Wissensbasis
│   ├── crawl.py           # Crawl4AI
│   ├── clean.py           # GDPR-Filter
│   └── build_kb.py        # Chunking & ChromaDB
├── klinik-daten/          # Beispiel-Markdown (optional)
├── tts-models/            # Piper-Sprachmodelle (nicht im Repo)
├── .env.example           # Beispiel-Konfiguration
├── requirements.txt
└── README.md
```

## Klinik-Daten verwalten

### Über das Dashboard

- **Daten laden:** URL einer Klinik-Webseite eingeben → Crawler holt den Inhalt → Wissensbasis wird befüllt
- **Wissensbasis leeren:** Button „Wissensbasis leeren“ – z.B. vor dem Laden einer anderen Klinik
- **Klinik wechseln:** Leeren → neue URL eingeben → Laden

### Manuell (Markdown-Dateien)

Sie können auch lokale Markdown-Dateien verwenden:

```bash
python -m scraper.build_kb --input klinik-daten/ --output chroma_db
```

Die Dateien in `klinik-daten/` (z.B. `leistungen.md`, `oeffnungszeiten.md`, `team.md`) dienen als Vorlage.

## API-Endpoints (Dashboard)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/status` | Agent-Status, aktuelle Klinik, Chunk-Anzahl |
| POST | `/api/agent/start?lang=de` | Agent starten (Sprache: de/en) |
| POST | `/api/agent/stop` | Agent beenden |
| POST | `/api/clinic/load` | Klinik-URL crawlen und Wissensbasis befüllen |
| POST | `/api/clinic/clear` | Wissensbasis leeren |
| PUT | `/api/language` | Sprache setzen |

## Booking-API

Die Booking-API läuft standardmäßig auf Port 8080. Endpoints:

- `GET /slots?date_param=2025-02-20` – verfügbare Slots
- `POST /book` – Termin buchen
- `GET /next-available` – nächster freier Termin
- `POST /cancel/{booking_id}` – Buchung stornieren

## Entwicklung & Tests

```bash
# Smoke-Test (Ollama, Piper, Whisper)
python scripts/smoke_test.py

# Pipeline-Test (ein Dialog-Turn)
python scripts/test_pipeline_one_turn.py
```

## Lizenz

Siehe [LICENSE](LICENSE) im Projektroot.

## Mitwirken

Contributions sind willkommen. Bitte öffnen Sie ein Issue oder einen Pull Request auf [GitHub](https://github.com/GunnarMUC/voice-agent-medspa-engdeu).

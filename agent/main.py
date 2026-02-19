"""
Voice Agent – LiveKit Integration.
Verbindet STT → RAG → LLM → TTS für den Zahnklinik-Telefonempfang.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Projekt-Root für relative Pfade (tts-models, chroma_db, etc.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)


def _create_booking_tools():
    """Function Tools für Terminbuchung (LLM Function Calling)."""
    from livekit.agents import function_tool

    @function_tool
    def get_available_slots(date: str) -> str:
        """Verfügbare Termin-Slots für ein Datum abrufen. Datum im Format YYYY-MM-DD."""
        import httpx
        from agent.config import get_settings
        s = get_settings()
        try:
            r = httpx.get(f"http://localhost:{s.booking_api_port}/slots", params={"date_param": date}, timeout=5)
            r.raise_for_status()
            data = r.json()
            slots = [s["slot_id"] for s in data.get("slots", [])[:5]]
            return f"Verfügbare Slots am {date}: " + ", ".join(slots) if slots else f"Keine Slots am {date}"
        except Exception as e:
            return f"Fehler beim Abrufen der Slots: {e}"

    @function_tool
    def book_appointment(slot_id: str, patient_name: str, patient_phone: str = "", treatment: str = "") -> str:
        """Termin buchen. slot_id Format: YYYY-MM-DD_HH:MM (z.B. 2026-02-20_10:00)."""
        import httpx
        from agent.config import get_settings
        s = get_settings()
        try:
            r = httpx.post(
                f"http://localhost:{s.booking_api_port}/book",
                json={
                    "slot_id": slot_id,
                    "patient": {"name": patient_name, "phone": patient_phone or None},
                    "treatment": treatment or None,
                },
                timeout=5,
            )
            r.raise_for_status()
            d = r.json()
            return f"Termin gebucht. Bestätigung: {d.get('date')} um {d.get('time')} für {d.get('patient_name')}."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return "Dieser Slot ist leider nicht mehr verfügbar. Bitte wählen Sie einen anderen."
            return f"Buchung fehlgeschlagen: {e.response.text}"
        except Exception as e:
            return f"Fehler bei der Buchung: {e}"

    @function_tool
    def get_next_available(treatment: str = "") -> str:
        """Nächsten freien Termin abrufen."""
        import httpx
        from agent.config import get_settings
        s = get_settings()
        try:
            r = httpx.get(
                f"http://localhost:{s.booking_api_port}/next-available",
                params={"treatment": treatment} if treatment else {},
                timeout=5,
            )
            r.raise_for_status()
            d = r.json()
            return f"Nächster freier Termin: {d.get('date')} um {d.get('time')} (Slot-ID: {d.get('slot_id')})"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "In den nächsten 14 Tagen sind leider keine Termine mehr frei."
            return f"Fehler: {e.response.text}"
        except Exception as e:
            return f"Fehler: {e}"

    return [get_available_slots, book_appointment, get_next_available]


def _create_agent():
    """Erstellt den Klinik-Assistenten Agent."""
    from livekit.agents import Agent

    return Agent(
        instructions="""Du bist der freundliche KI-Sprachassistent der Zahnklinik.
Du stellst dich als KI-System vor (GDPR).
Antworte kurz und natürlich – du sprichst, nicht schreibst.
Nutze die Tools für Terminbuchung und Verfügbarkeitsprüfung.
Bei Unklarheit nachfragen. Keine medizinischen Empfehlungen.""",
    )


def _create_session():
    """Erstellt AgentSession mit Ollama (lokal) + Silero VAD."""
    from livekit.agents import AgentSession
    from livekit.agents.voice import MultilingualModel
    from livekit.plugins import openai, silero

    from agent.config import get_settings

    s = get_settings()

    # Ollama via OpenAI-kompatibler API (lokal)
    llm = openai.LLM(
        model=s.ollama_model,
        base_url=f"{s.ollama_base_url.rstrip('/')}/v1",
        api_key="ollama",
    )

    # STT/TTS: LiveKit Inference (Cloud) – für lokale Alternativen siehe README
    # Für vollständig lokalen Betrieb: eigene STT/TTS-Plugins implementieren
    stt_model = os.getenv("STT_MODEL", "assemblyai/universal-streaming-multilingual")
    tts_model = os.getenv("TTS_MODEL", "cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")

    session = AgentSession(
        stt=stt_model,
        llm=llm,
        tts=tts_model,
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        tools=_create_booking_tools(),
    )
    return session


async def _run_agent(ctx):
    """Entrypoint für LiveKit Job."""
    from livekit.agents import JobContext
    from livekit.agents.voice import room_io

    session = _create_session()
    agent = _create_agent()

    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(),
    )

    await session.generate_reply(
        instructions="Begrüße den Anrufer mit: Hallo, Sie sprechen mit unserem KI-Assistenten. Wie kann ich Ihnen helfen?",
    )


def create_server():
    """Erstellt den AgentServer."""
    from livekit.agents import AgentServer

    server = AgentServer()

    @server.rtc_session(agent_name="klinik-agent")
    async def klinik_agent(ctx):
        await _run_agent(ctx)

    return server


def run_console_local():
    """
    Lokaler Konsolen-Modus – vollständig offline.
    STT (faster-whisper) → RAG → LLM (Ollama) → TTS (Piper).
    Kein LiveKit, keine Cloud-API-Keys nötig.
    """
    import sys

    try:
        import io
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    except ImportError:
        print("Bitte installieren: pip install sounddevice soundfile")
        sys.exit(1)

    from agent.config import get_settings
    from agent.llm import LLMEngine
    from agent.prompts import get_system_prompt, get_greeting
    from agent.rag import RAGEngine
    from agent.stt import STTEngine
    from agent.tts import TTSEngine

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    settings = get_settings()

    console.print(Panel("[bold]Voice Agent – Lokaler Konsolen-Modus[/bold]", style="blue"))
    console.print("Sprache wird automatisch erkannt (DE/EN). Beende mit 'Auf Wiedersehen' oder Ctrl+C.\n")

    stt = STTEngine()
    rag = RAGEngine()
    llm = LLMEngine()
    tts = TTSEngine()

    sample_rate = 16000  # für STT (faster-whisper erwartet 16kHz)
    lang = os.getenv("AGENT_DEFAULT_LANGUAGE", "de")

    def play_wav(wav_bytes: bytes) -> None:
        data, rate = sf.read(io.BytesIO(wav_bytes))
        sd.play(data, rate)
        sd.wait()

    # GDPR-Begrüßung als TTS
    greeting = get_greeting(lang)
    console.print(f"[dim]Agent: {greeting}[/dim]")
    try:
        audio = tts.synthesize(greeting, lang=lang)
        play_wav(audio)
    except Exception as e:
        console.print(f"[yellow]TTS: {e}[/yellow]")

    while True:
        try:
            console.print("\n[bold cyan]Sprechen Sie...[/bold cyan]")
            duration = 5  # Sekunden aufnehmen
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
            sd.wait()
            recording = recording.flatten()

            result = stt.transcribe(recording, vad_filter=True)
            text = result.text.strip()
            lang = result.language

            if not text:
                console.print("[dim](keine Sprache erkannt)[/dim]")
                continue

            console.print(f"[green]Sie:[/green] {text}")

            if any(w in text.lower() for w in ["auf wiedersehen", "tschüss", "bye", "goodbye"]):
                console.print("[dim]Agent: Auf Wiedersehen![/dim]")
                break

            # RAG + LLM
            rag_results = rag.search(text, top_k=2)
            rag_context = "\n".join(r["content"] for r in rag_results) if rag_results else ""
            system = get_system_prompt(lang, rag_context)

            response = llm.generate(text, system=system, stream=False)
            console.print(f"[blue]Agent:[/blue] {response}")

            # TTS
            try:
                audio = tts.synthesize(response, lang=lang)
                play_wav(audio)
            except Exception as e:
                console.print(f"[yellow]TTS: {e}[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[dim]Beendet.[/dim]")
            break


def main():
    """Startet den Agent (dev/start/console)."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "console-local":
        sys.argv.pop(1)
        run_console_local()
        return

    from livekit.agents import cli

    server = create_server()
    cli.run_app(server)


if __name__ == "__main__":
    main()

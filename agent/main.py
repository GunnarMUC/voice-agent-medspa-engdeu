"""
Voice Agent – LiveKit Integration + Console-Local Mode.
Verbindet STT → RAG → LLM → TTS für den Zahnklinik-Telefonempfang.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from agent.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

settings = get_settings()


def _create_booking_tools_livekit():
    """Function Tools für Terminbuchung (LiveKit Function Calling)."""
    from livekit.agents import function_tool

    @function_tool
    def get_available_slots(date: str) -> str:
        import httpx
        s = get_settings()
        try:
            r = httpx.get(f"http://localhost:{s.booking_api_port}/slots", params={"date_param": date}, timeout=5)
            r.raise_for_status()
            data = r.json()
            slots = [s["slot_id"] for s in data.get("slots", [])[:5]]
            return f"Verfuegbare Slots am {date}: " + ", ".join(slots) if slots else f"Keine Slots am {date}"
        except Exception as e:
            return f"Fehler beim Abrufen der Slots: {e}"

    @function_tool
    def book_appointment(slot_id: str, patient_name: str, patient_phone: str = "", treatment: str = "") -> str:
        import httpx
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
            return f"Termin gebucht. Bestaetigung: {d.get('date')} um {d.get('time')} fuer {d.get('patient_name')}."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return "Dieser Slot ist leider nicht mehr verfuegbar. Bitte waehlen Sie einen anderen."
            return f"Buchung fehlgeschlagen: {e.response.text}"
        except Exception as e:
            return f"Fehler bei der Buchung: {e}"

    @function_tool
    def get_next_available(treatment: str = "") -> str:
        import httpx
        s = get_settings()
        try:
            r = httpx.get(
                f"http://localhost:{s.booking_api_port}/next-available",
                params={"treatment": treatment} if treatment else {},
                timeout=5,
            )
            r.raise_for_status()
            d = r.json()
            return f"Naechster freier Termin: {d.get('date')} um {d.get('time')} (Slot-ID: {d.get('slot_id')})"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "In den naechsten 14 Tagen sind leider keine Termine mehr frei."
            return f"Fehler: {e.response.text}"
        except Exception as e:
            return f"Fehler: {e}"

    return [get_available_slots, book_appointment, get_next_available]


def _create_agent():
    from livekit.agents import Agent

    return Agent(
        instructions="""Du bist der freundliche KI-Sprachassistent der Zahnklinik.
Du stellst dich als KI-System vor (GDPR).
Antworte kurz und natuerlich – du sprichst, nicht schreibst.
Nutze die Tools fuer Terminbuchung und Verfuegbarkeitspruefung.
Bei Unklarheit nachfragen. Keine medizinischen Empfehlungen.""",
    )


def _create_session():
    from livekit.agents import AgentSession
    from livekit.agents.voice import MultilingualModel
    from livekit.plugins import openai, silero

    s = get_settings()

    llm = openai.LLM(
        model=s.ollama_model,
        base_url=f"{s.ollama_base_url.rstrip('/')}/v1",
        api_key="ollama",
    )

    # STT/TTS: Konfigurierbar via Umgebungsvariablen.
    # Default: AssemblyAI/Cartesia (Cloud). Für lokal: eigene Plugins implementieren.
    stt_model = os.getenv("LIVEKIT_STT_MODEL", "assemblyai/universal-streaming-multilingual")
    tts_model = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")

    session = AgentSession(
        stt=stt_model,
        llm=llm,
        tts=tts_model,
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        tools=_create_booking_tools_livekit(),
    )
    return session


async def _run_agent(ctx):
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
        instructions="Begruesse den Anrufer mit: Hallo, Sie sprechen mit unserem KI-Assistenten. Wie kann ich Ihnen helfen?",
    )


def create_server():
    from livekit.agents import AgentServer

    server = AgentServer()

    @server.rtc_session(agent_name="klinik-agent")
    async def klinik_agent(ctx):
        await _run_agent(ctx)

    return server


def _execute_booking_tool(tool_name: str, args: dict) -> str:
    """Führt ein Booking-Tool aus (für Console-Local Mode)."""
    import httpx

    s = get_settings()
    base = f"http://localhost:{s.booking_api_port}"

    try:
        if tool_name == "get_available_slots":
            date_str = args.get("date", "")
            r = httpx.get(f"{base}/slots", params={"date_param": date_str}, timeout=5)
            r.raise_for_status()
            data = r.json()
            slots = [sl["slot_id"] for sl in data.get("slots", [])[:5]]
            if slots:
                return f"Verfuegbare Termine am {date_str}: {', '.join(slots)}"
            return f"Am {date_str} sind leider keine Termine mehr frei."

        elif tool_name == "book_appointment":
            r = httpx.post(
                f"{base}/book",
                json={
                    "slot_id": args.get("slot_id", ""),
                    "patient": {
                        "name": args.get("patient_name", ""),
                        "phone": args.get("patient_phone", ""),
                    },
                    "treatment": args.get("treatment", ""),
                },
                timeout=5,
            )
            r.raise_for_status()
            d = r.json()
            return f"Termin erfolgreich gebucht! {d.get('date')} um {d.get('time')} fuer {d.get('patient_name')}. Buchungs-ID: {d.get('booking_id')}"

        elif tool_name == "get_next_available":
            treatment = args.get("treatment", "")
            params = {"treatment": treatment} if treatment else {}
            r = httpx.get(f"{base}/next-available", params=params, timeout=5)
            r.raise_for_status()
            d = r.json()
            return f"Naechster freier Termin: {d.get('date')} um {d.get('time')} (Slot: {d.get('slot_id')})"

        return f"Unbekanntes Tool: {tool_name}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return "Dieser Termin ist leider nicht mehr verfuegbar. Bitte waehlen Sie einen anderen."
        if e.response.status_code == 404:
            return "In den naechsten 14 Tagen sind leider keine Termine mehr frei."
        return f"Fehler bei der Anfrage: {e.response.text}"
    except Exception as e:
        return f"Fehler: {e}"


def _is_booking_query(text: str) -> bool:
    """Heuristik: Enthält die Eingabe eine Terminbuchungs-Absicht?"""
    keywords = [
        "termin", "buch", "reservier", "slot", "frei",
        "appointment", "book", "reserve", "available",
        "stornier", "absag", "cancel",
    ]
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def run_console_local():
    """
    Lokaler Konsolen-Modus – vollständig offline.
    STT (faster-whisper) → RAG → LLM (Ollama) → TTS (Piper).
    Mit Konversationsverlauf, Terminbuchung, VAD-basierter Aufnahme.
    """

    try:
        import io
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    except ImportError:
        print("Bitte installieren: pip install sounddevice soundfile numpy")
        sys.exit(1)

    from agent.llm import LLMEngine
    from agent.prompts import BOOKING_TOOLS, get_system_prompt, get_greeting
    from agent.rag import RAGEngine
    from agent.stt import STTEngine
    from agent.tts import TTSEngine

    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print(Panel("[bold]Voice Agent – Lokaler Konsolen-Modus[/bold]", style="blue"))
    console.print("Zweisprachig (DE/EN). Beende mit 'Auf Wiedersehen', 'bye' oder Ctrl+C.\n")

    stt = STTEngine()
    rag = RAGEngine()
    llm = LLMEngine()
    tts = TTSEngine()

    SAMPLE_RATE = 16000
    lang = settings.agent_default_language

    conversation_history: list[dict] = []
    booking_api_available = True

    def play_wav(wav_bytes: bytes) -> None:
        data, rate = sf.read(io.BytesIO(wav_bytes))
        sd.play(data, rate)
        sd.wait()

    def record_speech(
        sample_rate: int = 16000,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 15.0,
        min_duration: float = 0.5,
    ) -> np.ndarray:
        """VAD-basierte Sprachaufnahme: startet bei Sprache, stoppt nach Stille."""
        chunk_samples = int(sample_rate * 0.1)
        silence_samples = int(sample_rate * silence_duration)
        max_samples = int(sample_rate * max_duration)

        recording = []
        silent_frames = 0
        has_speech = False
        total_samples = 0

        stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype=np.float32)
        stream.start()
        try:
            while total_samples < max_samples:
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                total_samples += len(chunk)

                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms > silence_threshold:
                    has_speech = True
                    silent_frames = 0
                    recording.append(chunk)
                elif has_speech:
                    silent_frames += len(chunk)
                    recording.append(chunk)
                    if silent_frames >= silence_samples:
                        break
                else:
                    silent_frames = 0

                if not has_speech and len(recording) > 2 * silence_samples:
                    recording = recording[-silence_samples:]

                if not has_speech:
                    recording.append(chunk)
                    if len(recording) > sample_rate * 2:
                        recording = recording[-sample_rate:]

            stream.stop()
        finally:
            if stream.active:
                stream.stop()

        if recording:
            audio = np.concatenate(recording)
            if len(audio) < int(sample_rate * min_duration):
                return np.array([], dtype=np.float32)
            return audio
        return np.array([], dtype=np.float32)

    def cleanup():
        console.print("\n[dim]Raeume Ressourcen auf...[/dim]")
        try:
            sd.stop()
        except Exception:
            pass

    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), sys.exit(0)))

    greeting = get_greeting(lang)
    console.print(f"[dim]Agent: {greeting}[/dim]")
    conversation_history.append({"role": "assistant", "content": greeting})
    try:
        audio = tts.synthesize(greeting, lang=lang)
        play_wav(audio)
    except Exception as e:
        console.print(f"[yellow]TTS-Warnung: {e}[/yellow]")

    while True:
        try:
            console.print("\n[bold cyan]Sprechen Sie...[/bold cyan]")
            recording = record_speech(
                sample_rate=SAMPLE_RATE,
                silence_threshold=0.01,
                silence_duration=1.5,
                max_duration=15.0,
            )

            if len(recording) == 0:
                console.print("[dim](keine Sprache erkannt)[/dim]")
                continue

            result = stt.transcribe(recording, vad_filter=True)
            text = result.text.strip()
            lang = result.language

            if not text:
                console.print("[dim](keine Sprache erkannt)[/dim]")
                continue

            console.print(f"[green]Sie:[/green] {text}")
            conversation_history.append({"role": "user", "content": text})

            exit_words = ["auf wiedersehen", "tschüss", "bye", "goodbye", "auf wiederhören"]
            if any(w in text.lower() for w in exit_words):
                farewell = "Auf Wiedersehen! Wir freuen uns auf Ihren Besuch." if lang == "de" else "Goodbye! We look forward to your visit."
                console.print(f"[dim]Agent: {farewell}[/dim]")
                try:
                    audio = tts.synthesize(farewell, lang=lang)
                    play_wav(audio)
                except Exception:
                    pass
                break

            rag_results = rag.search(text, top_k=settings.rag_top_k)
            rag_context = "\n".join(r["content"] for r in rag_results) if rag_results else ""
            system = get_system_prompt(lang, rag_context)

            if _is_booking_query(text) and booking_api_available:
                try:
                    response, tool_calls = llm.generate_with_tools(
                        prompt=text,
                        system=system,
                        tools=BOOKING_TOOLS,
                        messages=conversation_history[:-1],
                        tool_handler=_execute_booking_tool,
                    )
                    if tool_calls:
                        console.print(f"[dim]Tool-Aufrufe: {[tc['name'] for tc in tool_calls]}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Tool-Calling fehlgeschlagen: {e}[/yellow]")
                    booking_api_available = False
                    response = llm.generate(text, system=system, stream=False)
            else:
                messages = [{"role": "system", "content": system}]
                messages.extend(conversation_history[:-1])
                response = llm.generate(text, messages=messages, stream=False)

            console.print(f"[blue]Agent:[/blue] {response}")
            conversation_history.append({"role": "assistant", "content": response})

            try:
                audio = tts.synthesize(response, lang=lang)
                play_wav(audio)
            except Exception as e:
                console.print(f"[yellow]TTS-Warnung: {e}[/yellow]")

        except KeyboardInterrupt:
            cleanup()
            break
        except Exception as e:
            console.print(f"[red]Fehler: {e}[/red]")
            continue

    cleanup()
    console.print("[dim]Agent beendet.[/dim]")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "console-local":
        sys.argv.pop(1)
        run_console_local()
        return

    from livekit.agents import cli

    server = create_server()
    cli.run_app(server)


if __name__ == "__main__":
    main()
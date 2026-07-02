"""
Speech-to-Text – faster-whisper Wrapper.
Transkribiert Audio und erkennt Sprache (de/en) für den Voice Agent.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
from faster_whisper import WhisperModel

from agent.config import get_settings


@dataclass
class TranscriptionResult:
    """Ergebnis einer Transkription."""

    text: str
    language: str  # "de" oder "en"
    language_probability: float


class STTEngine:
    """
    faster-whisper Wrapper für Speech-to-Text.
    Lädt Modell aus Config, transkribiert Audio, erkennt Sprache.
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        settings = get_settings()
        self.model_size = model_size or settings.whisper_model_size
        self.device = device or settings.whisper_device
        self.compute_type = compute_type or settings.whisper_compute_type
        self._model: Optional[WhisperModel] = None

    @property
    def model(self) -> WhisperModel:
        """Lazy-load Whisper-Modell."""
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio: Union[str, Path, np.ndarray],
        language: Optional[str] = None,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """
        Transkribiert Audio zu Text.

        Args:
            audio: Pfad zur Audiodatei, oder Audio-Bytes (16kHz, mono, float32)
            language: Optional "de" oder "en" – bei None wird erkannt
            vad_filter: VAD aktivieren (Stille filtern)

        Returns:
            TranscriptionResult mit text, language, language_probability
        """
        segments, info = self.model.transcribe(
            audio,
            language=language,
            vad_filter=vad_filter,
            without_timestamps=True,
        )
        text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()

        # Normalisiere Sprache auf de/en (Agent unterstützt nur diese)
        lang = info.language or "de"
        if lang not in ("de", "en"):
            lang = "de"  # Fallback auf Deutsch

        return TranscriptionResult(
            text=text,
            language=lang,
            language_probability=info.language_probability,
        )


def main() -> None:
    """Selbsttest: Lädt Modell und zeigt Konfiguration."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    settings = get_settings()

    console.print(Panel("[bold]STT (faster-whisper) Selbsttest[/bold]", style="blue"))
    console.print(f"Modell: {settings.whisper_model_size}")
    console.print(f"Device: {settings.whisper_device}")
    console.print(f"Compute: {settings.whisper_compute_type}")

    console.print("\n[dim]Lade Modell (kann beim ersten Mal dauern)...[/dim]")
    engine = STTEngine()
    console.print("[green]✓ Modell geladen[/green]")

    # Kurztest mit Stille (sollte leeren Text liefern)
    silent_audio = np.zeros(16000 * 2, dtype=np.float32)  # 2 Sekunden Stille
    result = engine.transcribe(silent_audio, vad_filter=False)
    console.print(f"\nStille-Test: text={repr(result.text)}, lang={result.language}")
    console.print("[green]✓ STT bereit[/green]")


if __name__ == "__main__":
    main()

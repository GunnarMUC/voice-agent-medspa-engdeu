"""
Text-to-Speech – Piper TTS Wrapper.
Generiert Audio aus Text, Sprache umschaltbar (de/en).
"""

from pathlib import Path
from typing import Optional, Union

from agent.config import get_settings


class TTSEngine:
    """
    Piper TTS Wrapper.
    Nutzt deutsche (Thorsten) und englische (Amy) Stimmen.
    """

    def __init__(
        self,
        de_model_path: Optional[str] = None,
        en_model_path: Optional[str] = None,
    ):
        settings = get_settings()
        self.de_model_path = Path(de_model_path or settings.tts_de_model_path)
        self.en_model_path = Path(en_model_path or settings.tts_en_model_path)

    def synthesize(
        self,
        text: str,
        lang: str = "de",
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Synthetisiert Text zu Audio.

        Args:
            text: Zu sprechender Text
            lang: "de" oder "en"
            output_path: Optional – speichert WAV-Datei

        Returns:
            WAV-Audio als bytes
        """
        import subprocess

        model = self.de_model_path if lang == "de" else self.en_model_path
        if not model.exists():
            raise FileNotFoundError(f"TTS-Modell nicht gefunden: {model}")

        args = [
            "piper",
            "--model",
            str(model),
            "--output_file",
            "-",  # stdout
        ]

        proc = subprocess.run(
            args,
            input=text.encode("utf-8"),
            capture_output=True,
            check=True,
        )
        audio_bytes = proc.stdout

        if output_path:
            Path(output_path).write_bytes(audio_bytes)

        return audio_bytes

    def synthesize_to_file(
        self,
        text: str,
        output_path: Union[str, Path],
        lang: str = "de",
    ) -> Path:
        """Synthetisiert und speichert WAV-Datei."""
        self.synthesize(text, lang=lang, output_path=str(output_path))
        return Path(output_path)


def main() -> None:
    """Selbsttest: Generiert kurze WAV-Datei."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    settings = get_settings()

    console.print(Panel("[bold]TTS (Piper) Selbsttest[/bold]", style="blue"))
    console.print(f"DE-Modell: {settings.tts_de_model_path}")
    console.print(f"EN-Modell: {settings.tts_en_model_path}")

    engine = TTSEngine()

    # Prüfe ob Modell existiert
    de_path = Path(settings.tts_de_model_path)
    if not de_path.is_absolute():
        de_path = Path.cwd() / de_path

    if not de_path.exists():
        console.print("[yellow]⚠ TTS-Modell nicht gefunden – bitte setup.sh ausführen[/yellow]")
        return

    out = Path("test_tts.wav")
    try:
        engine.synthesize("Hallo, dies ist ein Test.", lang="de", output_path=out)
        size = out.stat().st_size
        console.print(f"[green]✓ WAV erzeugt: {out} ({size} bytes)[/green]")
        out.unlink(missing_ok=True)
    except Exception as e:
        console.print(f"[red]❌ {e}[/red]")


if __name__ == "__main__":
    main()

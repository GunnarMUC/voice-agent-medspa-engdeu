"""
LLM – Ollama Wrapper für den Voice Agent.
Generiert Antworten mit Streaming-Support, vorbereitet für Function Calling.
"""

from typing import AsyncIterator, Iterator, Optional

from ollama import Client

from agent.config import get_settings


class LLMEngine:
    """
    Ollama Wrapper für LLM-Inferenz.
    Nutzt lokales Ollama für Gesprächsantworten.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self._client = Client(host=self.base_url)

    def health_check(self) -> bool:
        """Prüft ob Ollama läuft und Modell verfügbar ist."""
        try:
            resp = self._client.list()
            models = getattr(resp, "models", resp.get("models", [])) if resp else []
            prefix = self.model.split(":")[0]
            return any(
                getattr(m, "model", m.get("name", "")).startswith(prefix)
                for m in (models or [])
            )
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """
        Generiert Antwort auf Prompt.

        Args:
            prompt: Benutzer-Nachricht
            system: Optionaler System-Prompt
            stream: Bei True: Iterator über Tokens; bei False: vollständige Antwort

        Returns:
            str bei stream=False, Iterator[str] bei stream=True
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if stream:
            return self._stream(messages)
        return self._generate_sync(messages)

    def _generate_sync(self, messages: list) -> str:
        response = self._client.chat(model=self.model, messages=messages)
        return response["message"]["content"]

    def _stream(self, messages: list) -> Iterator[str]:
        stream = self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content


async def generate_async(
    prompt: str,
    system: Optional[str] = None,
) -> AsyncIterator[str]:
    """
    Async-Variante für LiveKit-Integration.
    """
    from ollama import AsyncClient

    settings = get_settings()
    client = AsyncClient(host=settings.ollama_base_url)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    stream = await client.chat(
        model=settings.ollama_model,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def main() -> None:
    """Selbsttest: Health-Check und kurze Generierung."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    engine = LLMEngine()

    console.print(Panel("[bold]LLM (Ollama) Selbsttest[/bold]", style="blue"))
    console.print(f"URL: {engine.base_url}")
    console.print(f"Modell: {engine.model}")

    if not engine.health_check():
        console.print("[red]❌ Ollama nicht erreichbar oder Modell fehlt[/red]")
        console.print("  Starte: ollama serve && ollama pull llama3.1:8b")
        return

    console.print("[green]✓ Ollama bereit[/green]")

    console.print("\n[dim]Test-Prompt: 'Sag kurz Hallo auf Deutsch'[/dim]")
    response = engine.generate("Sag kurz Hallo auf Deutsch.", stream=False)
    console.print(f"[green]Antwort:[/green] {response}")
    console.print("[green]✓ LLM bereit[/green]")


if __name__ == "__main__":
    main()

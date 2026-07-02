"""
LLM – Ollama Wrapper für den Voice Agent.
Generiert Antworten mit Streaming-Support, inkl. Tool/Function Calling.
"""

from typing import Any, AsyncIterator, Iterator, Optional

from ollama import Client

from agent.config import get_settings


class LLMEngine:
    """
    Ollama Wrapper für LLM-Inferenz.
    Nutzt lokales Ollama für Gesprächsantworten und Tool-Aufrufe.
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
        messages: Optional[list[dict]] = None,
    ) -> str | Iterator[str]:
        """
        Generiert Antwort auf Prompt.

        Args:
            prompt: Benutzer-Nachricht
            system: Optionaler System-Prompt
            stream: Bei True: Iterator über Tokens; bei False: vollständige Antwort
            messages: Optional – vollständige Nachrichtenliste (überschreibt prompt+system)

        Returns:
            str bei stream=False, Iterator[str] bei stream=True
        """
        if messages:
            msgs = messages
        else:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})

        if stream:
            return self._stream(msgs)
        return self._generate_sync(msgs)

    def generate_with_tools(
        self,
        prompt: str,
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        messages: Optional[list[dict]] = None,
        max_tool_rounds: int = 3,
        tool_handler: Optional[callable] = None,
    ) -> tuple[str, list[dict]]:
        """
        Generiert Antwort mit Tool-Calling-Unterstützung.

        Args:
            prompt: Benutzer-Nachricht
            system: Optionaler System-Prompt
            tools: Tool-Definitionen (Ollama-Format)
            messages: Optional – bestehende Nachrichtenliste (für Konversationsverlauf)
            max_tool_rounds: Maximale Anzahl Tool-Aufruf-Runden
            tool_handler: Funktion f(tool_name, args) → str (Tool-Ergebnis)

        Returns:
            Tuple aus (finale Antwort, Tool-Call-Historie)
        """
        if messages:
            msgs = list(messages)
        else:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        tool_calls_made = []

        for _ in range(max_tool_rounds):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": msgs,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._client.chat(**kwargs)

            has_tool_calls = False
            if response.get("message", {}).get("tool_calls"):
                has_tool_calls = True
                msg = response["message"]
                msgs.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": msg["tool_calls"]})

                for tc in msg["tool_calls"]:
                    func_name = tc.get("function", {}).get("name", "")
                    func_args = tc.get("function", {}).get("arguments", {})
                    tool_calls_made.append({"name": func_name, "arguments": func_args})

                    if tool_handler:
                        func_result = tool_handler(func_name, func_args)
                    else:
                        func_result = f"Tool {func_name} not available."

                    msgs.append({"role": "tool", "content": str(func_result)})

            if not has_tool_calls:
                final_text = response.get("message", {}).get("content", "")
                msgs.append({"role": "assistant", "content": final_text})
                return final_text, tool_calls_made

        final_text = "Entschuldigung, die Terminbuchung konnte nicht abgeschlossen werden. Bitte versuchen Sie es später erneut."
        return final_text, tool_calls_made

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

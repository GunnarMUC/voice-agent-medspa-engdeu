#!/usr/bin/env python3
"""
Test: Eine Pipeline-Runde (ohne Mikrofon).
Simuliert: User-Text → RAG → LLM → TTS (ohne Abspielen).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    from agent.config import get_settings
    from agent.llm import LLMEngine
    from agent.prompts import get_system_prompt
    from agent.rag import RAGEngine
    from agent.tts import TTSEngine

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    user_text = "Was kostet eine Zahnreinigung?"

    console.print(Panel("[bold]Pipeline-Test (1 Runde)[/bold]", style="blue"))
    console.print(f"[green]User:[/green] {user_text}")

    # RAG
    rag = RAGEngine()
    results = rag.search(user_text, top_k=2)
    rag_context = "\n".join(r["content"] for r in results) if results else ""
    console.print(f"[dim]RAG: {len(results)} Chunks[/dim]")

    # LLM
    system = get_system_prompt("de", rag_context)
    llm = LLMEngine()
    response = llm.generate(user_text, system=system, stream=False)
    console.print(f"[blue]Agent:[/blue] {response}")

    # TTS (nur synthetisieren, nicht abspielen)
    tts = TTSEngine()
    audio = tts.synthesize(response, lang="de")
    console.print(f"[dim]TTS: {len(audio)} bytes Audio[/dim]")

    console.print("\n[green]✓ Pipeline funktioniert[/green]")

if __name__ == "__main__":
    main()

"""
Wissensbasis aufbauen – Markdown/Dokumente → Chunks → Embeddings → ChromaDB.
"""

import re
from pathlib import Path
from typing import List, Optional

from agent.config import get_settings
from agent.rag import RAGEngine
from scraper.clean import clean_document


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[str]:
    """
    Teilt Text in überlappende Chunks.

    Args:
        text: Roher Text
        chunk_size: Zielgröße pro Chunk (Zeichen)
        chunk_overlap: Überlappung zwischen Chunks

    Returns:
        Liste von Text-Chunks
    """
    text = clean_document(text)
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]

        # Versuche an Satz- oder Absatzgrenze zu schneiden
        if end < text_len:
            last_newline = chunk.rfind("\n")
            last_period = max(
                chunk.rfind(". "),
                chunk.rfind("! "),
                chunk.rfind("? "),
            )
            break_at = max(last_newline, last_period)
            if break_at > chunk_size // 2:
                chunk = chunk[: break_at + 1]
                end = start + break_at + 1

        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap
        if start >= text_len:
            break

    return chunks


def load_markdown_files(directory: Path) -> List[str]:
    """Lädt alle .md Dateien aus einem Verzeichnis."""
    docs = []
    for path in directory.rglob("*.md"):
        docs.append(path.read_text(encoding="utf-8"))
    return docs


def build_knowledge_base(
    sources: List[str],
    chroma_path: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> int:
    """
    Baut die Wissensbasis aus Text-Quellen auf.

    Args:
        sources: Liste von Texten (Markdown, Plain-Text) oder Pfade zu .md Dateien
        chroma_path: Optional – ChromaDB-Pfad
        chunk_size: Optional – Chunk-Größe
        chunk_overlap: Optional – Überlappung

    Returns:
        Anzahl eingefügter Chunks
    """
    settings = get_settings()
    cs = chunk_size or settings.rag_chunk_size
    co = chunk_overlap or settings.rag_chunk_overlap

    all_chunks = []
    all_metas = []

    for i, src in enumerate(sources):
        if len(src) < 500 and Path(src).exists():
            p = Path(src)
            text = p.read_text(encoding="utf-8")
            source_name = p.stem
        else:
            text = src
            source_name = f"doc_{i}"

        chunks = chunk_text(text, chunk_size=cs, chunk_overlap=co)
        for c in chunks:
            all_chunks.append(c)
            all_metas.append({"source": source_name})

    if not all_chunks:
        return 0

    engine = RAGEngine(chroma_path=chroma_path)
    engine.add_documents(all_chunks, metadatas=all_metas)
    return len(all_chunks)


def main() -> None:
    """Baut Wissensbasis aus klinik-daten/ Verzeichnis."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    data_dir = Path(__file__).resolve().parent.parent / "klinik-daten"

    console.print(Panel("[bold]Wissensbasis aufbauen[/bold]", style="blue"))

    if not data_dir.exists():
        console.print(f"[yellow]⚠ {data_dir} nicht gefunden – erstelle Verzeichnis[/yellow]")
        data_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(data_dir.rglob("*.md"))
    if not md_files:
        console.print("[red]Keine .md Dateien in klinik-daten/[/red]")
        return

    # Pfade übergeben – build_knowledge_base lädt die Dateien
    sources = [str(p) for p in md_files]
    count = build_knowledge_base(sources)
    console.print(f"[green]✓ {count} Chunks in ChromaDB geladen[/green]")


if __name__ == "__main__":
    main()

"""
RAG – ChromaDB + Ollama Embeddings.
Sucht im Klinik-Wissen nach relevanten Chunks für LLM-Kontext.
"""

from typing import List, Optional

from agent.config import get_settings


class RAGEngine:
    """
    RAG-Pipeline: ChromaDB mit Ollama nomic-embed-text.
    Lädt Dokumente, sucht ähnliche Chunks.
    """

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        embed_model: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        settings = get_settings()
        self.chroma_path = str(chroma_path or settings.chroma_path)
        self.embed_model = embed_model or settings.ollama_embed_model
        self.top_k = top_k or settings.rag_top_k
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Lazy-init ChromaDB Collection."""
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="klinik_wissen",
                metadata={"description": "Klinik-FAQ, Behandlungen, Preise"},
            )
        return self._collection

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Erzeugt Embeddings via Ollama /api/embed."""
        import httpx

        settings = get_settings()
        payload = {"model": self.embed_model, "input": texts if len(texts) > 1 else texts[0]}
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/embed",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Response: {"embeddings": [[...], ...]} oder {"embedding": [...]}
        embs = data.get("embeddings", data.get("embedding"))
        if embs is None:
            return []
        if isinstance(embs[0], (int, float)):
            return [embs]  # single embedding
        return embs

    def search(self, query: str, top_k: Optional[int] = None) -> List[dict]:
        """
        Sucht nach relevanten Chunks.

        Args:
            query: Suchanfrage (z.B. "Was kostet eine Zahnreinigung?")
            top_k: Anzahl Ergebnisse (default aus Config)

        Returns:
            Liste von {"content": str, "metadata": dict, "distance": float}
        """
        k = top_k or self.top_k
        collection = self._get_collection()

        if collection.count() == 0:
            return []

        query_embedding = self._embed([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        out = []
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        dists = results["distances"][0] if results["distances"] else []

        for doc, meta, dist in zip(docs, metas, dists):
            out.append({
                "content": doc or "",
                "metadata": meta or {},
                "distance": dist,
            })
        return out

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """Fügt Dokumente zur Wissensbasis hinzu."""
        collection = self._get_collection()
        embeddings = self._embed(documents)
        meta = metadatas or [{}] * len(documents)
        doc_ids = ids or [f"doc_{i}" for i in range(len(documents))]
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=meta,
            ids=doc_ids,
        )

    def clear(self) -> int:
        """Leert die Wissensbasis. Returns bisherige Chunk-Anzahl."""
        collection = self._get_collection()
        count = collection.count()
        if count > 0:
            ids = collection.get(include=[])["ids"]
            collection.delete(ids=ids)
        return count


def main() -> None:
    """Selbsttest: Sucht in (leerer) DB oder fügt Beispieldaten hinzu."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    engine = RAGEngine()

    console.print(Panel("[bold]RAG (ChromaDB) Selbsttest[/bold]", style="blue"))
    console.print(f"Chroma-Pfad: {engine.chroma_path}")
    console.print(f"Embed-Modell: {engine.embed_model}")

    collection = engine._get_collection()
    count = collection.count()
    console.print(f"Dokumente in DB: {count}")

    if count == 0:
        console.print("\n[dim]Füge Beispieldaten hinzu...[/dim]")
        engine.add_documents(
            [
                "Zahnreinigung kostet 80 Euro.",
                "Öffnungszeiten: Mo–Fr 8–18 Uhr.",
                "Wir bieten Implantate und Veneers an.",
            ],
            metadatas=[{"source": "faq"}, {"source": "info"}, {"source": "leistungen"}],
        )
        console.print("[green]✓ 3 Chunks eingefügt[/green]")

    results = engine.search("Was kostet Zahnreinigung?", top_k=2)
    console.print(f"\nSuche 'Was kostet Zahnreinigung?': {len(results)} Treffer")
    for r in results:
        console.print(f"  - {r['content'][:60]}... (dist={r['distance']:.3f})")
    console.print("[green]✓ RAG bereit[/green]")


if __name__ == "__main__":
    main()

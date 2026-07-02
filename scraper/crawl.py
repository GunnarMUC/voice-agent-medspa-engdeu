"""
Web-Crawler – Crawl4AI Integration.
Scrapt Klinik-Webseiten zu Markdown für die Wissensbasis.
"""

import asyncio
from pathlib import Path
from typing import Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter


async def crawl_url(
    url: str,
    output_path: Optional[Path] = None,
    use_pruning: bool = True,
) -> str:
    """
    Crawlt eine URL und extrahiert Markdown-Content.

    Args:
        url: Zu crawlende URL
        output_path: Optional – speichert Markdown in Datei
        use_pruning: PruningContentFilter für weniger Boilerplate

    Returns:
        Extrahierter Markdown-Text
    """
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.5, min_word_threshold=30)
        if use_pruning
        else None,
        options={"ignore_links": True, "ignore_images": True},
    )
    config = CrawlerRunConfig(markdown_generator=md_generator)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            raise RuntimeError(f"Crawl fehlgeschlagen: {result.error_message}")

        md_obj = result.markdown
        text = md_obj.fit_markdown if (use_pruning and md_obj.fit_markdown) else md_obj.raw_markdown
        text = text or ""

        if output_path:
            Path(output_path).write_text(text, encoding="utf-8")

        return text


def crawl_url_sync(url: str, output_path: Optional[Path] = None) -> str:
    """Synchrone Wrapper für crawl_url."""
    return asyncio.run(crawl_url(url, output_path))


def main() -> None:
    """Selbsttest: Crawlt Beispiel-URL."""
    import sys
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

    console.print(Panel(f"[bold]Crawl4AI Test: {url}[/bold]", style="blue"))
    try:
        text = crawl_url_sync(url)
        console.print(f"[green]✓ {len(text)} Zeichen extrahiert[/green]")
        console.print(f"\n[dim]Vorschau (erste 500 Zeichen):[/dim]\n{text[:500]}...")
    except Exception as e:
        console.print(f"[red]❌ {e}[/red]")


if __name__ == "__main__":
    main()

"""
Command-Line Interface for the Pinecone Hybrid Search RAG Pipeline.
"""

import argparse
import sys
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .config import settings
from .pipeline import HybridRAGPipeline
from .parsers.output_parsers import RAGResponse

console = Console()


def handle_index(args):
    """Indexes files or directories into Pinecone with hybrid vectors."""
    console.print(Panel("[bold green]Pinecone Hybrid Search - Document Indexer[/bold green]"))

    pipeline = HybridRAGPipeline(mock_mode=args.mock)
    target = Path(args.target)

    if not target.exists():
        console.print(f"[bold red]Target path does not exist:[/bold red] {target}")
        sys.exit(1)

    console.print(f"Indexing target: [cyan]{target}[/cyan] (Mock mode: {pipeline.mock_mode})")
    count = pipeline.ingest_files(target)
    console.print(f"[bold green]Successfully indexed {count} document chunks![/bold green]")


def handle_search(args):
    """Executes raw hybrid search and displays ranked results with scores."""
    console.print(Panel(f"[bold blue]Hybrid Search[/bold blue]\nQuery: [yellow]{args.query}[/yellow]\nAlpha: {args.alpha} (0.0=BM25, 1.0=Dense, 0.5=Hybrid)"))

    pipeline = HybridRAGPipeline(mock_mode=args.mock, alpha=args.alpha, top_k=args.top_k)
    results = pipeline.search(query=args.query, alpha=args.alpha, top_k=args.top_k)

    if not results:
        console.print("[yellow]No matching documents found.[/yellow]")
        return

    table = Table(title=f"Hybrid Search Results (Top {len(results)})")
    table.add_column("Rank", justify="center", style="cyan", no_wrap=True)
    table.add_column("ID / Chunk", style="magenta")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Source", style="blue")
    table.add_column("Content Snippet", style="white")

    for i, res in enumerate(results, 1):
        snippet = (res.content[:150] + "...") if len(res.content) > 150 else res.content
        table.add_row(
            str(i),
            res.id,
            f"{res.score:.4f}",
            str(res.metadata.get("source", "N/A")),
            snippet.replace("\n", " "),
        )

    console.print(table)


def handle_query(args):
    """Runs complete RAG: Hybrid Retrieval -> LLM -> LangChain Output Parser."""
    console.print(Panel(f"[bold magenta]RAG Pipeline Query[/bold magenta]\nQuestion: [yellow]{args.question}[/yellow]\nAlpha: {args.alpha} | Structured Output: {args.structured}"))

    pipeline = HybridRAGPipeline(mock_mode=args.mock, alpha=args.alpha, top_k=args.top_k)
    output = pipeline.query(
        question=args.question,
        alpha=args.alpha,
        top_k=args.top_k,
        structured=args.structured,
    )

    # 1. Show Retrieved Context
    console.print(f"\n[bold cyan]1. Retrieved Chunks via Hybrid Search ({len(output['retrieved_chunks'])}):[/bold cyan]")
    for i, doc in enumerate(output["retrieved_chunks"], 1):
        source = doc.metadata.get("source", "unknown")
        score = doc.metadata.get("hybrid_score", 0.0)
        console.print(f"  [{i}] [bold]{source}[/bold] (score: {score:.4f}): {doc.page_content[:120]}...")

    # 2. Show Parsed Answer
    console.print(f"\n[bold green]2. LangChain Output Parser Result:[/bold green]")
    resp = output["response"]

    if isinstance(resp, RAGResponse):
        console.print(Panel(Markdown(resp.answer), title="[bold green]Answer (Parsed by PydanticOutputParser)[/bold green]"))

        if resp.citations:
            cit_table = Table(title="Verified Document Citations")
            cit_table.add_column("Source", style="cyan")
            cit_table.add_column("Chunk ID", style="magenta")
            cit_table.add_column("Snippet Quote", style="white")
            cit_table.add_column("Relevance", style="yellow")
            for c in resp.citations:
                cit_table.add_row(c.source, c.chunk_id or "N/A", c.snippet, c.relevance or "N/A")
            console.print(cit_table)

        console.print(f"[bold]Confidence Score:[/bold] [yellow]{resp.confidence_score * 100:.1f}%[/yellow]")

        if resp.follow_up_questions:
            console.print("[bold cyan]Follow-up Questions:[/bold cyan]")
            for q in resp.follow_up_questions:
                console.print(f"  • {q}")
    else:
        console.print(Panel(str(resp), title="[bold green]Answer (Parsed by StrOutputParser)[/bold green]"))


def handle_demo(args):
    """Runs a complete end-to-end demonstration with sample documents."""
    console.print(Panel.fit("[bold green]RAG Pipeline Demo: Pinecone Hybrid Search & LangChain Parsers[/bold green]", subtitle="End-to-End Walkthrough"))

    sample_dir = settings.sample_docs_dir if settings.sample_docs_dir.exists() else Path("sample_docs")
    if not sample_dir.exists():
        console.print(f"[bold red]Sample directory '{sample_dir}' not found.[/bold red]")
        return

    # Ingest sample documents
    console.print("[bold cyan]Step 1: Document Ingestion and Parsing[/bold cyan]")
    console.print("Ingesting Markdown, Text, and JSON documents using LangChain Loaders & Recursive Splitter...")

    pipeline = HybridRAGPipeline(mock_mode=args.mock or not bool(settings.pinecone_api_key))
    pipeline.ingest_files(sample_dir)

    # Demonstrate Hybrid Search with different alpha weights
    test_queries = [
        ("What is the alpha parameter in hybrid search?", 0.5),
        ("PydanticOutputParser schema validation", 0.3),
        ("dotproduct metric Pinecone Serverless", 0.7),
    ]

    console.print("\n[bold cyan]Step 2: Hybrid Search Retrieval Across Differing Alpha Weights[/bold cyan]")
    for query_text, alpha_val in test_queries:
        console.print(f"\n[yellow]Query:[/yellow] '{query_text}' with [bold]alpha={alpha_val}[/bold]:")
        results = pipeline.search(query_text, alpha=alpha_val, top_k=2)
        for rank, res in enumerate(results, 1):
            source = res.metadata.get("source", "N/A")
            console.print(f"  Match #{rank} (score: {res.score:.4f}, source: {source}): {res.content[:100]}...")

    # Demonstrate End-to-End RAG with LangChain Pydantic Output Parser
    console.print("\n[bold cyan]Step 3: Full RAG Query with LangChain Pydantic Output Parser[/bold cyan]")
    rag_query = "How do LangChain output parsers and hybrid search alpha weighting work together?"
    output = pipeline.query(rag_query, alpha=0.5, structured=True)

    resp = output["response"]
    if isinstance(resp, RAGResponse):
        console.print(Panel(Markdown(resp.answer), title="[bold green]Synthesized Answer[/bold green]"))
        console.print(f"[bold]Parsed Confidence Score:[/bold] {resp.confidence_score * 100:.1f}%")
        if resp.citations:
            console.print(f"[bold]Citations ({len(resp.citations)}):[/bold]")
            for c in resp.citations:
                console.print(f"  • Source: [cyan]{c.source}[/cyan] - quote: \"{c.snippet}\"")
        if resp.follow_up_questions:
            console.print(f"[bold]Suggested Follow-ups:[/bold]")
            for fq in resp.follow_up_questions:
                console.print(f"  - {fq}")
    else:
        console.print(f"Response: {resp}")

    console.print("\n[bold green]✓ Demo completed successfully![/bold green]")


def main():
    parser = argparse.ArgumentParser(description="Pinecone Hybrid Search RAG Pipeline with LangChain Parsers")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Index command
    idx_parser = subparsers.add_parser("index", help="Index documents into Pinecone")
    idx_parser.add_argument("target", help="File or directory path to index")
    idx_parser.add_argument("--mock", action="store_true", help="Run with in-memory mock store instead of live Pinecone")

    # Search command
    search_parser = subparsers.add_parser("search", help="Execute hybrid search query")
    search_parser.add_argument("query", help="Query string")
    search_parser.add_argument("--alpha", type=float, default=settings.hybrid_alpha, help="Alpha weight: 0.0=BM25, 1.0=Dense, 0.5=Hybrid")
    search_parser.add_argument("--top-k", type=int, default=settings.top_k, help="Number of results to retrieve")
    search_parser.add_argument("--mock", action="store_true", help="Run in mock mode")

    # Query command
    query_parser = subparsers.add_parser("query", help="Run full RAG pipeline (Retrieve + Generate + Parse)")
    query_parser.add_argument("question", help="User question")
    query_parser.add_argument("--alpha", type=float, default=settings.hybrid_alpha, help="Alpha weight")
    query_parser.add_argument("--top-k", type=int, default=settings.top_k, help="Top K context chunks")
    query_parser.add_argument("--no-structured", dest="structured", action="store_false", help="Use StrOutputParser instead of PydanticOutputParser")
    query_parser.add_argument("--mock", action="store_true", help="Run in mock mode")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run end-to-end sample walkthrough")
    demo_parser.add_argument("--mock", action="store_true", help="Force mock mode")

    args = parser.parse_args()

    if args.command == "index":
        handle_index(args)
    elif args.command == "search":
        handle_search(args)
    elif args.command == "query":
        handle_query(args)
    elif args.command == "demo":
        handle_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

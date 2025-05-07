"""Human in the loop workflow to find a document and then conduct one or more searches within it."""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from cpr_sdk.models.search import Passage, Filters, Hit
from cpr_sdk.tools_agents.tools.search import (
    search_within_document,
    search_for_documents_by_title,
)

console = Console()


def display_search_results(documents: list[Hit]) -> None:
    """Display search results in a readable format."""

    if not documents:
        console.print("[bold red]No results found.[/bold red]")
        return

    console.print(Panel("[bold]Document Search Results[/bold]", style="cyan"))

    doc_table = Table(show_header=True)
    doc_table.add_column("#", style="dim")
    doc_table.add_column("Document Title", style="cyan")
    doc_table.add_column("Family", style="green")
    doc_table.add_column("Source", style="yellow")
    doc_table.add_column("Type", style="blue")
    doc_table.add_column("ID", style="dim")
    doc_table.add_column("Geographies", style="magenta")

    for i, doc in enumerate(documents, 1):
        doc_table.add_row(
            str(i),
            doc.document_title or "Untitled",
            doc.family_name or "Unknown",
            doc.family_source or "Unknown",
            doc.document_content_type or "Unknown",
            doc.document_import_id or "No ID",
            ", ".join(doc.family_geographies) if doc.family_geographies else "Unknown",
        )

    console.print(doc_table)


def display_passages(passages: list[Passage]) -> None:
    """Display passage search results in a readable format."""

    if not passages:
        console.print("[bold red]No matching passages found.[/bold red]")
        return

    for i, passage in enumerate(passages, 1):
        console.print(
            Panel(
                f"{passage.text_block}",
                title=f"[bold]Passage {i}[/bold]",
                border_style="blue",
            )
        )


def search_document_workflow(
    filters: Optional[Filters] = None,
    limit: int = 20,
) -> None:
    """Run the interactive workflow to find a document and search within it."""

    # Step 1: Initial search to find a document
    console.print(Panel("[bold]Document Search[/bold]", style="cyan"))
    initial_query = Prompt.ask("Enter search query to find a document")

    with console.status("[bold green]Searching database...[/bold green]"):
        documents = search_for_documents_by_title(
            query=initial_query,
            limit=limit,
        )

    display_search_results(documents)  # type: ignore

    if not documents:
        console.print(
            "[bold red]No documents found. Please try a different search.[/bold red]"
        )
        return

    # Step 2: Select a document
    while True:
        selection = Prompt.ask(
            f"Select a document [dim](1-{len(documents)}) or 'q' to quit[/dim]"
        )
        if selection.lower() == "q":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(documents):
                selected_document = documents[idx]
                document_id = selected_document.document_import_id
                if document_id is None:
                    console.print("[bold red]Selected document has no ID.[/bold red]")
                    continue
                console.print(
                    f"\nSelected document: [bold cyan]{selected_document.document_title}[/bold cyan] [dim](ID: {document_id})[/dim]"
                )
                break
            else:
                console.print(
                    f"[yellow]Please enter a number between 1 and {len(documents)}[/yellow]"
                )
        except ValueError:
            console.print("[yellow]Please enter a valid number or 'q'[/yellow]")

    # Step 3: Search within the document
    while True:
        console.print(Panel("[bold]Search Within Document[/bold]", style="cyan"))
        doc_query = Prompt.ask("Enter search query for the document (or 'q' to quit)")

        if doc_query.lower() == "q":
            break

        doc_limit = IntPrompt.ask("Maximum passages to return", default=100)
        doc_exact_match = Confirm.ask("Use exact matching?", default=False)

        with console.status("[bold green]Searching within document...[/bold green]"):
            passages = search_within_document(
                document_id=document_id,
                query=doc_query,
                limit=doc_limit,
                filters=filters,
                exact_match=doc_exact_match,
            )

        display_passages(passages)


app = typer.Typer()


@app.command()
def main() -> None:
    """Find a document and search within it interactively."""
    try:
        search_document_workflow()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Workflow interrupted.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {e}")


if __name__ == "__main__":
    app()

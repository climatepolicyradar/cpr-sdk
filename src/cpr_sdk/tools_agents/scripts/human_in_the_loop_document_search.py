"""Human in the loop workflow to find a document and then conduct one or more searches within it."""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from cpr_sdk.models.search import Family, Passage, Filters, Document
from cpr_sdk.tools_agents.tools.search import search_database, search_within_document

console = Console()


def display_search_results(families: list[Family]) -> None:
    """Display search results in a readable format."""

    if not families:
        console.print("[bold red]No results found.[/bold red]")
        return

    for i, family in enumerate(families, 1):
        documents = [hit for hit in family.hits if isinstance(hit, Document)]
        family_name = documents[0].family_name
        family_description = documents[0].family_description
        family_source = documents[0].family_source

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row(
            f"[bold cyan]{i}. {family_name}[/bold cyan] [dim](ID: {family.id})[/dim]"
        )
        table.add_row(f"[yellow]Source:[/yellow] {family_source}")

        if family_description:
            table.add_row(
                f"[yellow]Description:[/yellow] {family_description[:100]}..."
            )

        for document in documents:
            table.add_row(
                f"[green]Document:[/green] {document.document_title} [dim]({document.document_slug})[/dim]"
            )

        console.print(Panel(table, expand=False))


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
) -> None:
    """Run the interactive workflow to find a document and search within it."""

    # Step 1: Initial search to find a document
    console.print(Panel("[bold]Document Search[/bold]", style="cyan"))
    initial_query = Prompt.ask("Enter search query to find a document")

    limit = IntPrompt.ask("Maximum number of results to return", default=20)
    max_hits = IntPrompt.ask("Maximum hits per family", default=10)
    exact_match = Confirm.ask("Use exact matching?", default=False)

    with console.status("[bold green]Searching database...[/bold green]"):
        families = search_database(
            query=initial_query,
            limit=limit,
            max_hits_per_family=max_hits,
            filters=filters,
            exact_match=exact_match,
        )

    display_search_results(families)

    if not families:
        console.print(
            "[bold red]No documents found. Please try a different search.[/bold red]"
        )
        return

    # Step 2: Select a family
    while True:
        selection = Prompt.ask(
            f"Select a document [dim](1-{len(families)}) or 'q' to quit[/dim]"
        )
        if selection.lower() == "q":
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(families):
                selected_family: Family = families[idx]
                break
            else:
                console.print(
                    f"[yellow]Please enter a number between 1 and {len(families)}[/yellow]"
                )
        except ValueError:
            console.print("[yellow]Please enter a valid number or 'q'[/yellow]")

    documents = [hit for hit in selected_family.hits if isinstance(hit, Document)]
    console.print(
        f"\nSelected family: [bold cyan]{documents[0].family_name}[/bold cyan] [dim](ID: {selected_family.id})[/dim]"
    )

    # Step 3: Select a specific document within the family
    if not documents:
        console.print("[bold red]No documents found in this family.[/bold red]")
        return

    console.print(Panel("[bold]Documents in Selected Family[/bold]", style="cyan"))

    doc_table = Table(show_header=True)
    doc_table.add_column("#", style="dim")
    doc_table.add_column("Title", style="cyan")
    doc_table.add_column("Type", style="green")
    doc_table.add_column("ID", style="dim")

    for i, doc in enumerate(documents, 1):
        doc_table.add_row(
            str(i),
            doc.document_title or "Untitled",
            doc.document_content_type or "Unknown",
            doc.document_import_id,
        )

    console.print(doc_table)

    while True:
        doc_selection = Prompt.ask(
            f"Select a document [dim](1-{len(documents)}) or 'q' to quit[/dim]"
        )
        if doc_selection.lower() == "q":
            return

        try:
            doc_idx = int(doc_selection) - 1
            if 0 <= doc_idx < len(documents):
                selected_document = documents[doc_idx]
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

    # Step 4: Search within the document
    while True:
        console.print(Panel("[bold]Search Within Document[/bold]", style="cyan"))
        doc_query = Prompt.ask("Enter search query for the document (or 'q' to quit)")

        if doc_query.lower() == "q":
            break

        doc_limit = IntPrompt.ask("Maximum passages to return", default=20)
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

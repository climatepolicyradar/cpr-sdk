import time
from contextlib import nullcontext
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from cpr_sdk.config import VESPA_URL
from cpr_sdk.models.search import (
    ConceptFilter,
    Document,
    Passage,
    SearchParameters,
    SearchResponse,
)
from cpr_sdk.search_adaptors import VespaSearchAdapter
from cpr_sdk.vespa import build_vespa_request_body, parse_vespa_response

SCORES_NUM_DECIMALS = 3

app = typer.Typer()


def get_rank_feature_names(search_response: SearchResponse) -> list[str]:
    """
    Get names of rank features from a search response.

    Rank features surface the scores given to individual parts of the query, and are
    defined in the Vespa schema.
    """
    rank_feature_names = set()
    for family in search_response.results:
        for hit in family.hits:
            if hit.rank_features:
                rank_feature_names.update(
                    k for k in hit.rank_features.keys() if not k.startswith("vespa")
                )
    rank_feature_names = sorted(list(rank_feature_names))

    return rank_feature_names


def add_tokens_summary_to_yql(yql: str) -> str:
    """Amend the summary requested in a YQL query to return tokens."""

    return yql.replace("summary(search_summary)", "summary(search_summary_with_tokens)")


@app.command()
def main(
    query: str = typer.Argument(..., help="The search query to run."),
    exact_match: bool = False,
    limit: int = 20,
    show_rank_features: bool = False,
    page_results: bool = typer.Option(
        default=True,
        help="Whether to use the default terminal pager to show results. Disable with `--no-page-results` if you want to redirect the output to a file.",
    ),
    experimental_tokens: bool = typer.Option(
        default=False,
        help="Whether to include tokens in the summary. Tokens are not in the final Vespa response model, so this requires setting a breakpoint on the raw response.",
    ),
    concept_id: list[str] = typer.Option(
        default=[],
        help="Filter results by concept ID. Can be used multiple times in the same run.",
    ),
    distance_threshold: Optional[float] = typer.Option(
        default=None,
        help="Optional threshold for the vector component of hybrid search. Passages with an inner product score below this threshold will be excluded.",
    ),
):
    """Run a search query with different rank profiles."""
    console = Console()
    search_adapter = VespaSearchAdapter(VESPA_URL)
    search_parameters = SearchParameters(
        query_string=query,
        exact_match=exact_match,
        limit=limit,
        concept_filters=[
            ConceptFilter(name="id", value=concept_id) for concept_id in concept_id
        ],
        distance_threshold=distance_threshold,
    )
    request_body = build_vespa_request_body(search_parameters)

    if experimental_tokens:
        print(
            "WARNING: tokens are not fed into the final Vespa response, so you will see no change unless you set a breakpoint just after `search_response_raw` following these lines."
        )
        request_body["yql"] = add_tokens_summary_to_yql(request_body["yql"])

    start_time = time.time()
    search_response_raw = search_adapter.client.query(body=request_body)
    request_time = time.time() - start_time

    # Debugging steps for showing tokens
    # from rich import print as rprint
    # rprint(search_response_raw.json)
    # breakpoint()

    search_response = parse_vespa_response(search_response_raw)  # type: ignore[arg-type]
    n_results = len(search_response.results)
    rank_feature_names = get_rank_feature_names(search_response)

    pager = console.pager(styles=True, links=True) if page_results else nullcontext()

    with pager:
        console.print(Markdown("# Query"))
        console.print(f"Text: {query}")
        console.print(f"Exact match: {exact_match}")
        console.print(f"Limit: {limit}")
        console.print(f"Request time: {request_time:.3f}s")
        console.print("Request body:")
        console.print_json(data=request_body)

        console.print(Markdown("# Families"))
        table = Table(show_header=True, header_style="bold", show_lines=True)
        table.add_column("Family Name")
        table.add_column("Geography")
        table.add_column("Score")
        table.add_column("Hits")
        table.add_column("Slug")

        for family in search_response.results:
            family_data = family.hits[0].model_dump()
            table.add_row(
                family_data["family_name"],
                family_data["family_geography"],
                str(round(family_data["relevance"], SCORES_NUM_DECIMALS)),
                str(len(family.hits)),
                family_data["family_slug"],
            )

        console.print(table)

        console.print(Markdown("# Results"))

        for idx, family in enumerate(search_response.results, start=1):
            family_data = family.hits[0].model_dump()
            console.rule(
                title=f"Family {idx}/{n_results}: '{family_data['family_name']}' ({family_data['family_geography']}). Score: {round(family_data['relevance'], 3)}"
            )
            family_url = f"https://app.climatepolicyradar.org/document/{family_data['family_slug']}"
            details = f"""
            [bold]Total hits:[/bold] {len(family.hits)}
            [bold]Family:[/bold] [link={family_url}]{family_data["family_import_id"]}[/link]
            [bold]Family slug:[/bold] {family_data["family_slug"]}
            [bold]Geography:[/bold] {family_data["family_geography"]}
            [bold]Relevance:[/bold] {family_data["relevance"]}
            """

            console.print(details)
            console.print(
                f"[bold]Description:[/bold] {family_data['family_description']}"
            )
            console.print("\n[bold]Hits:[/bold]")

            # Create table headers
            table = Table(show_header=True, header_style="bold", show_lines=True)
            table.add_column("Text")
            table.add_column("Score")
            table.add_column("Type")
            table.add_column("TB ID")
            table.add_column("Doc ID")
            if show_rank_features:
                for feature_name in rank_feature_names:
                    table.add_column(feature_name)

            for hit in family.hits:
                if isinstance(hit, Passage):
                    hit_type = "Text block"
                    text = hit.text_block
                    tb_id = hit.text_block_id
                    doc_id = hit.document_import_id
                elif isinstance(hit, Document):
                    hit_type = "Document"
                    text = "<see family description>"
                    tb_id = "-"
                    doc_id = hit.document_import_id
                else:
                    raise ValueError(f"Whoops! Unknown hit type {type(hit)}")

                rank_feature_values = (
                    [hit.rank_features.get(name) for name in rank_feature_names]
                    if (show_rank_features and hit.rank_features is not None)
                    else []
                )
                rank_feature_values = [
                    str(round(v, SCORES_NUM_DECIMALS)) if v is not None else "-"
                    for v in rank_feature_values
                ]

                table.add_row(
                    text,
                    (
                        str(round(hit.relevance, SCORES_NUM_DECIMALS))
                        if hit.relevance is not None
                        else "n/a"
                    ),
                    hit_type,
                    tb_id,
                    doc_id,
                    *rank_feature_values,
                )

            console.print(table)


if __name__ == "__main__":
    app()

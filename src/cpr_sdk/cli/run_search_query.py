import json
from rich.console import Console
from rich.table import Table
from rich import print_json
from rich import print as rprint
import typer
from src.cpr_sdk.search_adaptors import VespaSearchAdapter
from src.cpr_sdk.models.search import SearchParameters
from tests.conftest import VESPA_TEST_SEARCH_URL


def main(
    instance_url: str = VESPA_TEST_SEARCH_URL,
    exact_match: bool = False,
    limit: int = 10,
):
    """Run a search query with different rank profiles."""
    console = Console()
    search_adapter = VespaSearchAdapter(instance_url)

    while True:
        query = input("Enter your search query (or 'q' to quit): ")
        if query.lower() == "q":
            break

        search_parameters = SearchParameters(
            query_string=query, exact_match=exact_match, limit=limit
        )
        search_response = search_adapter.search(search_parameters)

        for family in search_response.families:
            family_data = family.hits[0].model_dump()
            console.rule(
                title=f"{family_data['family_name']} ({family_data['family_geography']} ,{family_data['family_import_id']})"
            )
            print_json(
                json.dumps(
                    {
                        k: v
                        for k, v in family_data.items()
                        if not k.startswith("text_block") and "metadata" not in k
                    },
                    default=str,
                )
            )

            # There's some typing weirdness going on here:
            # hasattr(family.hits[0], 'text_blocks') can be False, but
            # family.hits[0].text_block exists
            try:
                rprint("Text blocks:")
                table = Table(title="Hits Table")

                # Add columns to the table
                table.add_column(
                    "Text Block ID", justify="right", style="cyan", no_wrap=True
                )
                table.add_column("Text Block", style="magenta")

                # Add rows to the table
                for hit in family.hits:
                    try:
                        table.add_row(f"{hit.text_block_id}", f"{hit.text_block}")  # type: ignore
                    except Exception:
                        pass

                # Print the table
                console.print(table)

                if family == search_response.families[-1]:
                    print("No more families to show.")
                    break
            except AttributeError:
                print("No text blocks found.")

            input("Press any key to show next family")


if __name__ == "__main__":
    typer.run(main)

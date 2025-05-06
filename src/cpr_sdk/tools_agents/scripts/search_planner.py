"""
Use an AI agent to help plan a search.

TODO: the in-document search doesn't have any usefulness here unless you provide a document ID
or URL.
"""

from rich import print as rprint
from pydantic_ai import Agent
from pydantic_ai.agent import InstrumentationSettings

import typer

from cpr_sdk.tools_agents.tools.search import search_database


def plan_search(query: str, pdf: bool = False) -> None:
    """Plan a search for a given query."""

    search_agent = Agent(
        model="google-gla:gemini-1.5-pro",
        instrument=InstrumentationSettings(event_mode="logs"),
        system_prompt="""
        You are a helpful assistant that helps plan a search on a database of climate laws and policies, litigation cases
        and other documents.
        
        You will be given a query from a user, and will need to translate this into a useful search query for the `search_database` tool.
        You can use the `search_database` tool's `return_type` parameter to control whether you return documents or passages.
        
        When you answer, quote the text exactly as it appears in the each document you search. Also quote each document you use in your answer directly.
        
        If you can't find any evidence to support the user's query, just say so.
        """,
        tools=[search_database],
    )
    result = search_agent.run_sync(query)

    rprint(result.all_messages_json())
    print(result.output)


if __name__ == "__main__":
    typer.run(plan_search)

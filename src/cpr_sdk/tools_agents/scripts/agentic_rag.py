"""Use an AI agent to help plan a search."""

from typing import Callable

from pydantic_ai import Agent
from pydantic_ai.agent import InstrumentationSettings

import typer

from cpr_sdk.tools_agents.tools.search import search_within_document, search_database
from cpr_sdk.tools_agents.tools.genai import prompt_pdf


def do_rag(query: str, pdf: bool = False) -> None:
    """Plan a search for a given query."""

    tools: list[Callable] = [
        search_database,
    ]

    if pdf:
        tools.append(prompt_pdf)
    else:
        tools.append(search_within_document)

    search_agent = Agent(
        model="google-gla:gemini-1.5-pro",
        instrument=InstrumentationSettings(event_mode="logs"),
        system_prompt="""
        You are a helpful assistant that helps plan a search on a database of climate laws and policies, litigation cases
        and other documents.
        
        You will be given a query from a user, and you will need to plan a search to find the most relevant documents. Feel free to conduct multiple searches if necessary to answer the query. 
        For example, if you find a document which might contain an answer to the user's query, you can conduct a search within that document.
        
        When you answer, quote the text exactly as it appears in the each document you search (as well as the details of the document it comes from) to support your answer.
        
        If you can't find any evidence to support the user's query, just say so.
        """,
        tools=tools,
    )
    result = search_agent.run_sync(query)

    print(result.output)


if __name__ == "__main__":
    typer.run(do_rag)

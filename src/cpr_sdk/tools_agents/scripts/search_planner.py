"""Use an AI agent to help plan a search."""

from pydantic_ai import Agent
from pydantic_ai.agent import InstrumentationSettings

from cpr_sdk.tools_agents.tools.search import search_within_document, search_database
from cpr_sdk.tools_agents.tools.genai import GENAI_MODEL_PROVIDER


search_agent = Agent(
    model=GENAI_MODEL_PROVIDER,
    instrument=InstrumentationSettings(event_mode="logs"),
    system_prompt="""
    You are a helpful assistant that helps plan a search on a database of climate laws and policies, litigation cases
    and other documents.
    
    You will be given a query from a user, and you will need to plan a search to find the most relevant documents. Feel free to conduct multiple searches if necessary to answer the query. 
    For example, if you find a document which might contain an answer to the user's query, you can conduct a search within that document.
    
    When you answer, quote the text exactly as it appears in the each document you search (as well as the details of the document it comes from) to support your answer.
    
    If you can't find any evidence to support the user's query, just say so.
    """,
    tools=[
        search_within_document,
        search_database,
    ],
)


def plan_search(query: str) -> str:
    """Plan a search for a given query."""
    result = search_agent.run_sync(query)
    return result.output


if __name__ == "__main__":
    query = input("Enter a query: ")
    print(plan_search(query))

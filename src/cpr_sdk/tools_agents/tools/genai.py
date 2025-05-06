from typing import Optional, Type

from pydantic_ai import Agent, DocumentUrl
from pydantic import BaseModel

GENAI_PROVIDER = "google-gla"
GENAI_MODEL = "gemini-2.0-flash"
GENAI_MODEL_PROVIDER = f"{GENAI_PROVIDER}:{GENAI_MODEL}"


def _get_agent() -> Agent:
    return Agent(GENAI_MODEL_PROVIDER)


def prompt_pdf(
    document_url: str, prompt: str, output_type: Optional[Type[BaseModel]] = None
) -> str | BaseModel:
    agent = _get_agent()
    result = agent.run_sync(
        [
            prompt,
            DocumentUrl(url=document_url),
        ],
        output_type=output_type,
    )
    return result.output

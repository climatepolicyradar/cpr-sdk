# Tools and Agents

**Tools** are functions which enable common tasks using our infrastructure and data. **Agents** are users of those tools.

This submodule enables the following:

* easy access to tools: common or powerful operations completed using our data (e.g. semantically searching a document, searching the whole corpus, or asking a question about a PDF using generative AI)
* scripts which can perform tasks made of multiple actions which use our system. E.g. a task like "get all the targets in countries' latest NDCs" should be easy to achieve with a script
* research into how well AI agents can use these tools to accomplish complex tasks

## Setup

1. Install this submodule's dependency group: `poetry install --with tools_agents.
2. Add any API keys needed to `.env`.  Using Gemini (default) requires a valid `GEMINI_API_KEY`.
3. Try one of the examples in `scripts/`

## Requirements (in progress)

Tools:

* [x] run our product search
* [x] search within a document
* [x] search for documents based on their titles (rather than family titles)

* [x] use an AI service to ask a question of a PDF
* [] arbitrarily prompt an LLM, with pydantic models for inputs and outputs

Scripts/agent flows:

* [x] simple human in the loop searches
* [x] agent plans searches and returns results
  * TODO: clear models returned by search
* [ ] manual: given URLs, use the PDF tool to answer a prompt about policies in policies
  * [ ] adjust this example to use the in-document search tool instead. use pydantic-ai's usage tracking to compare the cost of each.

Extras:

* [] add logging to tools so you know what's being called
* [] refactor the search CLI to use the tools

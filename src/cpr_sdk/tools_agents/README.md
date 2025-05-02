# Tools and Agents

**Tools** are functions which enable common tasks using our infrastructure and data. **Agents** are users of those tools.

This submodule enables the following:

* easy access to tools: common or powerful operations completed using our data (e.g. semantically searching a document, searching the whole corpus, or asking a question about a PDF using generative AI)
* scripts which can perform tasks made of multiple actions which use our system. E.g. a task like "get all the targets in countries' latest NDCs" should be easy to achieve with a script
* research into how well AI agents can use these tools to accomplish complex tasks

## Setup

1. Install this submodule's dependency group: `poetry install --with tools_agents

## Requirements (in progress)

Tools:

* [x] run our product search
* [x] search within a document
* [] search for documents based on their titles

* [x] use an AI service to ask a question of a PDF
* [] arbitrarily prompt an LLM, with pydantic models for inputs and outputs


Scripts/agent flows:

* [x] simple human in the loop searches
* [ ] agent plans searches and returns results (will require clear models returned by search)
* [ ] ask a question of a document's PDF given its name or URL

Extras:

* [] genAI tools have centralised config
* [] refactor the search CLI to use the tools

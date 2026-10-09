---
name: ai-agents-catalog
description: Search a curated catalog of AI agent projects (CrewAI, AutoGen, Agno, LangGraph, LangChain, LlamaIndex, by industry) and point to the repository or runnable example that fits a need. Use when the user asks for an agent example, a framework choice, or a starting project for a use case.
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# AI Agents Catalog

Offline index of the projects listed in
[500-AI-Agents-Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects) (MIT licence).
`catalog.json` holds each entry: name, framework, industry, description, url
(and `local` for the runnable examples under `agents/`).

## Search

```bash
python3 {baseDir}/scripts/search.py [-f FRAMEWORK] [-i INDUSTRY] [-n 15] keyword ...
python3 {baseDir}/scripts/search.py --list-facets      # available frameworks / industries
```

Present the best matches with their link. Do not claim a project works or is maintained
without checking its repository.

## Running a listed project

Entries are third-party code. Before running one: read its README and dependencies, use a
virtualenv or sandbox, and never give it production keys or confidential documents.
Runnable examples (`local` field) live in the upstream repo under `agents/<name>/`
(`pip install -r requirements.txt`, copy `.env.example` to `.env`, `python agent.py`).

## Refresh the catalog

```bash
git clone --depth 1 https://github.com/ashishpatel26/500-AI-Agents-Projects /tmp/500agents
python3 {baseDir}/scripts/build_catalog.py /tmp/500agents {baseDir}/catalog.json
```

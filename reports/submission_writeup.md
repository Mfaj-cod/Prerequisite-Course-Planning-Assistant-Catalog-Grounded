# Purple Merit Assessment 1 Write-Up

## Chosen Catalog / Sources

- Institution: The University of Texas at Dallas, 2025 Undergraduate Catalog
- Sources include Computer Science and Software Engineering degree requirement pages, academic policy pages, degree plan policy pages, and curated CS/SE/ECS course descriptions.
- The source manifest is generated automatically in `data/processed/source_manifest.json` with URL, access date, and notes.

## Architecture Overview

- Ingestion fetches official UT Dallas pages, normalizes sections, and stores raw plus processed artifacts.
- Retrieval uses `BAAI/bge-small-en-v1.5` embeddings with a persisted local Chroma vector store.
- A symbolic prerequisite engine evaluates eligibility and plan feasibility for correctness before any LLM phrasing step.
- Groq is used as the optional final drafting layer, while correctness remains grounded in retrieved and parsed catalog data.

## Chunking / Retrieval Tradeoffs

- Sections are chunked to roughly 800-token-equivalent windows with overlap so prerequisite sentences stay intact.
- Retrieval starts with top-k similarity search and the assistant emits citations using source URL, heading, and chunk id.

## Evaluation Summary

- Citation coverage rate: 80.0%
- Eligibility correctness: 86.67%
- Abstention accuracy: 100%

## Failure Modes / Next Improvements

- The current planner models curated major buckets rather than the entire university core.
- Some catalog wording patterns would benefit from a richer symbolic parser for advisor exceptions and program-substitution rules.
- A next iteration would add stronger reranking, richer plan explanations, and a deeper curriculum graph for multi-term planning.
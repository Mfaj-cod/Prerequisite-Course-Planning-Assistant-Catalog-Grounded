# Purple Merit Assessment 1: Short Write-Up

**Chosen catalog / institution**  
The University of Texas at Dallas, 2025 Undergraduate Catalog. Corpus: 4 program/policy pages plus 37 curated CS/SE/ECS course pages from the same catalog. Full source list is in `data/processed/source_manifest.json`. Accessed: **2026-03-27**.

**Key sources**
- https://catalog.utdallas.edu/2025/undergraduate/programs/ecs/computer-science
- https://catalog.utdallas.edu/2025/undergraduate/programs/ecs/software-engineering
- https://catalog.utdallas.edu/2025/undergraduate/policies/academic
- https://catalog.utdallas.edu/2025/undergraduate/policies/degree-plans

**Architecture overview**  
HTML catalog pages -> normalization and section extraction -> section-aware chunking -> `BAAI/bge-small-en-v1.5` embeddings -> Chroma vector store -> retrieval plus symbolic prerequisite evaluator -> Groq-backed response drafting. The symbolic layer determines eligibility and plan feasibility; the LLM explains and formats the result with citations.

**Chunking / retrieval choices and tradeoffs**  
I used section-preserving chunks of about 800 token-equivalent words with about 120-token overlap so prerequisite sentences, grade constraints, and co-requisite wording stay intact. Retrieval uses Chroma similarity search (`k=8`) and keeps a smaller cited set for final answers. This improves grounding, but some abstention-heavy cases lower citation coverage because unsupported questions intentionally return no evidence-backed claim.

**Prompts / agent roles (high level)**  
The pipeline is staged as: Intake/Router, Catalog Retriever, Planner/Responder, and Verifier. Intake asks clarifying questions when catalog year, program, grades, or next-term load are missing. Retriever pulls catalog evidence only. Planner combines retrieved evidence with symbolic prerequisite checks to produce either a prerequisite decision or a next-term plan. Verifier blocks unsupported claims and forces the required abstention behavior when the answer is not in the catalog.

**Evaluation summary**  
25 queries: 10 prerequisite checks, 5 multi-hop prerequisite chain questions, 5 program-rule questions, and 5 not-in-docs questions. Results: citation coverage **80.0%**, eligibility correctness **86.67%**, abstention accuracy **100%**.

**Key failure modes / next improvements**  
The current planner models major buckets well, but it does not fully compute the entire university core or every advisor exception path. Some prerequisite wording patterns still need richer symbolic parsing for substitutions, waivers, and standing nuances. Next improvements would be stronger reranking, broader degree-audit coverage, and a deeper curriculum graph for multi-term planning.

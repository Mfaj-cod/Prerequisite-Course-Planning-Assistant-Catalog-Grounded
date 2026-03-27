# Catalog-Grounded Course Planning Assistant

Prerequisite and term-planning assistant grounded in the UT Dallas 2025 undergraduate catalog.

## What this project does

- Fetches and normalizes official UT Dallas catalog pages.
- Builds a local Chroma index with `BAAI/bge-small-en-v1.5` embeddings.
- Uses a symbolic prerequisite evaluator for eligibility decisions and term planning.
- Uses Groq for optional grounded answer synthesis when `GROQ_API_KEY` is configured.
- Runs a 25-case evaluation suite and generates submission-ready reports.
- Includes a Streamlit demo.

## Quick start

1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Configure Groq if you want live LLM phrasing:

```powershell
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env`.

3. Build the corpus and vector index.
This step needs internet access for the official UT Dallas pages and the first-time embedding model download.

```powershell
python -m src.catalog_assistant.cli ingest --force
```

4. Run a sample prerequisite question:

```powershell
python -m src.catalog_assistant.cli ask --query "Can I take CS 4347 next term?" --profile-file data/samples/sample_profile_cs.json
```

5. Run a planning example:

```powershell
python -m src.catalog_assistant.cli plan --profile-file data/samples/sample_profile_cs.json
```

6. Run evaluation and generate reports:

```powershell
python -m src.catalog_assistant.cli eval
```

7. Launch the demo:

```powershell
streamlit run app.py
```

## Project layout

- `src/catalog_assistant/`: core package
- `data/samples/`: sample student profiles
- `data/eval/`: evaluation cases
- `data/processed/`: normalized corpus and source manifest
- `reports/`: generated evaluation summaries and submission write-up

## Notes

- Groq is optional at runtime for development, but the codepath is integrated and used whenever `GROQ_API_KEY` is available.
- The assistant refuses availability and instructor-specific questions unless that information is explicitly present in the catalog pages.
- Regular `ask`, `plan`, and `eval` runs use the locally cached embedding model after the first successful ingest.

